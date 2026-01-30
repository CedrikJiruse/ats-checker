//! Interactive menu for CLI.

use crate::config::Config;
use crate::error::Result;
use crate::input::InputHandler;

use crate::processor::ResumeProcessor;
use crate::scraper::{cache::CacheConfig, retry::RetryConfig};
use crate::scraper::{
    jobspy::JobSpyScraper, CacheWrapper, JobScraperManager, RetryWrapper, SavedSearch,
    SavedSearchManager, SearchFilters,
};
use crate::state::StateManager;
use crate::utils::file::sanitize_filename;
use crate::utils::ocr::{check_tesseract_installed, extract_text_from_image};
use std::collections::VecDeque;
use std::io::{self, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

// -------------------------
// Menu History
// -------------------------

/// Tracks recent operations for history display.
#[derive(Debug, Clone)]
pub struct OperationHistory {
    operations: VecDeque<String>,
    max_size: usize,
}

impl OperationHistory {
    /// Create a new operation history with default size.
    pub fn new() -> Self {
        Self {
            operations: VecDeque::with_capacity(10),
            max_size: 10,
        }
    }

    /// Add an operation to history.
    pub fn add(&mut self, operation: &str) {
        if self.operations.len() >= self.max_size {
            self.operations.pop_front();
        }
        self.operations.push_back(operation.to_string());
    }

    /// Get recent operations.
    pub fn recent(&self, n: usize) -> Vec<&String> {
        self.operations.iter().rev().take(n).collect()
    }

    /// Check if history is empty.
    pub fn is_empty(&self) -> bool {
        self.operations.is_empty()
    }
}

impl Default for OperationHistory {
    fn default() -> Self {
        Self::new()
    }
}

// -------------------------
// Main Interactive Menu
// -------------------------

/// Run the interactive menu.
///
/// # Errors
///
/// Returns an error if any menu operation fails (e.g., file I/O, processing errors).
pub async fn run_interactive_menu(config: Config) -> Result<()> {
    // Set up Ctrl+C handler
    let running = Arc::new(AtomicBool::new(true));
    let r = running.clone();
    ctrlc::set_handler(move || {
        r.store(false, Ordering::SeqCst);
        println!("\n\nReceived interrupt signal. Cleaning up...");
    })
    .expect("Error setting Ctrl-C handler");

    let mut history = OperationHistory::new();

    println!("\n{}", "=".repeat(60));
    println!("ATS RESUME CHECKER - Interactive Mode");
    println!("{}", "=".repeat(60));
    println!("Keyboard shortcuts: q=quit, h=history, c=config, s=state");

    loop {
        if !running.load(Ordering::SeqCst) {
            println!("Exiting gracefully. Goodbye!");
            break;
        }

        println!("\n{}", "-".repeat(60));
        println!("MAIN MENU");
        println!("{}", "-".repeat(60));
        println!("1. Process resumes");
        println!("2. Job search");
        println!("3. View available files");
        println!("4. View configuration");
        println!("5. View state (processed resumes)");
        println!("6. View outputs");
        println!("7. Settings");
        println!("8. Test OCR");
        println!("9. View history");
        println!("10. Check API keys");
        println!("11. Setup JobSpy (job scraping)");
        println!("0. Exit (or press 'q')");
        println!("{}", "-".repeat(60));

        print!("\nEnter your choice: ");
        io::stdout().flush().unwrap();

        let mut input = String::new();
        io::stdin().read_line(&mut input).unwrap();
        let choice = input.trim();

        // Handle keyboard shortcuts
        match choice {
            "q" | "Q" | "0" => {
                history.add("Exit");
                println!("\nExiting. Goodbye!");
                break;
            }
            "h" | "H" => {
                view_history(&history);
                continue;
            }
            "c" | "C" => {
                view_config(&config);
                history.add("View configuration (shortcut)");
                continue;
            }
            "s" | "S" => {
                if let Err(e) = view_state(&config) {
                    eprintln!("Error: {e}");
                } else {
                    history.add("View state (shortcut)");
                }
                continue;
            }
            _ => {}
        }

        match choice {
            "1" => {
                if let Err(e) = process_resumes_menu(&config).await {
                    eprintln!("Error: {e}");
                } else {
                    history.add("Process resumes");
                }
            }
            "2" => {
                if let Err(e) = job_search_menu(&config).await {
                    eprintln!("Error: {e}");
                } else {
                    history.add("Job search");
                }
            }
            "3" => {
                view_files_menu(&config);
                history.add("View available files");
            }
            "4" => {
                view_config(&config);
                history.add("View configuration");
            }
            "5" => {
                if let Err(e) = view_state(&config) {
                    eprintln!("Error: {e}");
                } else {
                    history.add("View state");
                }
            }
            "6" => {
                view_outputs_menu(&config);
                history.add("View outputs");
            }
            "7" => {
                settings_menu(&config);
                history.add("Settings");
            }
            "8" => {
                test_ocr_menu();
                history.add("Test OCR");
            }
            "9" => {
                view_history(&history);
            }
            "10" => {
                check_api_keys_menu();
                history.add("Check API keys");
            }
            "11" => {
                jobspy_setup_menu();
                history.add("Setup JobSpy");
            }
            _ => {
                println!("Invalid choice. Please try again.");
            }
        }
    }

    Ok(())
}

// -------------------------
// Process Resumes Menu
// -------------------------

async fn process_resumes_menu(config: &Config) -> Result<()> {
    println!("\n{}", "-".repeat(60));
    println!("PROCESS RESUMES");
    println!("{}", "-".repeat(60));
    println!("1. Process all resumes");
    println!("2. Process specific resume");
    println!("3. Process resume with job description");
    println!("4. Interactive resume selection");
    println!("0. Back to main menu");
    println!("{}", "-".repeat(60));

    print!("\nEnter your choice: ");
    io::stdout().flush().unwrap();

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();
    let choice = input.trim();

    let mut processor = ResumeProcessor::new(config.clone())?;

    match choice {
        "1" => {
            println!("\nProcessing all resumes...");
            let results = processor.process_all_resumes().await?;

            let successful = results.iter().filter(|r| r.success).count();
            let failed = results.len() - successful;

            println!("\n{}", "=".repeat(60));
            println!("PROCESSING COMPLETE");
            println!("{}", "=".repeat(60));
            println!(
                "Total: {} | Successful: {} | Failed: {}",
                results.len(),
                successful,
                failed
            );

            if failed > 0 {
                println!("\nFailed resumes:");
                for result in results.iter().filter(|r| !r.success) {
                    if let Some(err) = &result.error {
                        println!("  - {err}");
                    }
                }
            }
        }
        "2" => {
            print!("\nEnter resume path: ");
            io::stdout().flush().unwrap();

            let mut resume_path = String::new();
            io::stdin().read_line(&mut resume_path).unwrap();
            let resume_path = resume_path.trim();

            println!("\nProcessing {resume_path}...");
            let result = processor.process_resume(resume_path, None).await?;

            if result.success {
                println!("\n✓ Resume processed successfully!");
                if let Some(scores) = result.scores {
                    println!("  Score: {:.2}/100", scores.total);
                }
                if let Some(output_dir) = result.output_dir {
                    println!("  Output: {}", output_dir.display());
                }
            }
        }
        "3" => {
            print!("\nEnter resume path: ");
            io::stdout().flush().unwrap();

            let mut resume_path = String::new();
            io::stdin().read_line(&mut resume_path).unwrap();
            let resume_path = resume_path.trim();

            print!("Enter job description path: ");
            io::stdout().flush().unwrap();

            let mut job_path = String::new();
            io::stdin().read_line(&mut job_path).unwrap();
            let job_path = job_path.trim();

            println!("\nProcessing {resume_path} with job {job_path}...");
            let result = processor
                .process_resume(resume_path, Some(job_path))
                .await?;

            if result.success {
                println!("\n✓ Resume processed successfully!");
                if let Some(scores) = result.scores {
                    println!("  Score: {:.2}/100", scores.total);
                }
                if let Some(output_dir) = result.output_dir {
                    println!("  Output: {}", output_dir.display());
                }
            }
        }
        "4" => {
            select_resume_interactive(config, &mut processor).await?;
        }
        "0" => {}
        _ => {
            println!("Invalid choice.");
        }
    }

    Ok(())
}

async fn select_resume_interactive(config: &Config, processor: &mut ResumeProcessor) -> Result<()> {
    let input_handler = InputHandler::new(
        config.input_resumes_folder.clone(),
        config.job_descriptions_folder.clone(),
    );

    let resumes = input_handler.list_resumes()?;

    if resumes.is_empty() {
        println!(
            "\nNo resumes found in {}",
            config.input_resumes_folder.display()
        );
        return Ok(());
    }

    println!("\nAvailable resumes:");
    for (i, file) in resumes.iter().enumerate() {
        println!("  {}. {}", i + 1, file.display());
    }
    println!("  0. Cancel");

    print!("\nSelect resume number: ");
    io::stdout().flush().unwrap();

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();

    if let Ok(num) = input.trim().parse::<usize>() {
        if num == 0 {
            return Ok(());
        }
        if let Some(resume) = resumes.get(num - 1) {
            println!("\nProcessing {}...", resume.display());
            let result = processor
                .process_resume(resume.to_str().unwrap_or(""), None)
                .await?;

            if result.success {
                println!("\n✓ Resume processed successfully!");
                if let Some(scores) = result.scores {
                    println!("  Score: {:.2}/100", scores.total);
                }
                if let Some(output_dir) = result.output_dir {
                    println!("  Output: {}", output_dir.display());
                }
            }
        } else {
            println!("Invalid selection.");
        }
    } else {
        println!("Invalid input.");
    }

    Ok(())
}

// -------------------------
// Job Search Menu
// -------------------------

async fn job_search_menu(config: &Config) -> Result<()> {
    println!("\n{}", "-".repeat(60));
    println!("JOB SEARCH");
    println!("{}", "-".repeat(60));
    println!("1. New job search");
    println!("2. View saved searches");
    println!("3. Run saved search");
    println!("4. Create saved search");
    println!("5. Delete saved search");
    println!("0. Back to main menu");
    println!("{}", "-".repeat(60));

    print!("\nEnter your choice: ");
    io::stdout().flush().unwrap();

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();
    let choice = input.trim();

    let results_folder = config.job_search_results_folder.clone();
    let saved_searches_path = config.saved_searches_file.clone();

    match choice {
        "1" => {
            new_job_search(&results_folder, &saved_searches_path).await?;
        }
        "2" => {
            view_saved_searches(&saved_searches_path)?;
        }
        "3" => {
            run_saved_search(&results_folder, &saved_searches_path).await?;
        }
        "4" => {
            create_saved_search(&saved_searches_path)?;
        }
        "5" => {
            delete_saved_search(&saved_searches_path)?;
        }
        "0" => {}
        _ => {
            println!("Invalid choice.");
        }
    }

    Ok(())
}

async fn new_job_search(results_folder: &PathBuf, saved_searches_path: &PathBuf) -> Result<()> {
    print!("\nEnter search keywords (e.g., 'software engineer'): ");
    io::stdout().flush().unwrap();
    let mut keywords = String::new();
    io::stdin().read_line(&mut keywords).unwrap();

    print!("Enter location (optional, press Enter to skip): ");
    io::stdout().flush().unwrap();
    let mut location = String::new();
    io::stdin().read_line(&mut location).unwrap();

    print!("Remote only? (y/n): ");
    io::stdout().flush().unwrap();
    let mut remote = String::new();
    io::stdin().read_line(&mut remote).unwrap();
    let remote_only = remote.trim().to_lowercase() == "y";

    print!("Max results (default 50): ");
    io::stdout().flush().unwrap();
    let mut max_results = String::new();
    io::stdin().read_line(&mut max_results).unwrap();
    let max_results: i32 = max_results.trim().parse().unwrap_or(50);

    let mut filters = SearchFilters::default();
    if !keywords.trim().is_empty() {
        filters.keywords = Some(keywords.trim().to_string());
    }
    if !location.trim().is_empty() {
        filters.location = Some(location.trim().to_string());
    }
    filters.remote_only = remote_only;

    println!("\nInitializing job scrapers...");
    let mut manager = JobScraperManager::new(results_folder, saved_searches_path)?;

    // Register available scrapers
    let sources = vec!["linkedin", "indeed", "glassdoor", "google", "ziprecruiter"];
    let retry_config = RetryConfig::default();
    let cache_config = CacheConfig::default();

    for source in &sources {
        if let Ok(scraper) = JobSpyScraper::new(source) {
            if scraper.check_dependencies().is_ok() {
                let retry_scraper = RetryWrapper::new(scraper, retry_config.clone());
                let cached_scraper = CacheWrapper::new(retry_scraper, cache_config.clone());
                manager.register_scraper(Box::new(cached_scraper));
                println!("  ✓ Registered {source} scraper");
            }
        }
    }

    if manager.available_sources().is_empty() {
        println!("\n⚠ No scrapers available. Please ensure Python and JobSpy are installed.");
        return Ok(());
    }

    println!("\nSearching for jobs...");
    let available_scrapers = manager.available_sources();
    match manager
        .search_jobs(&filters, &available_scrapers, max_results)
        .await
    {
        Ok(jobs) => {
            println!("\n✓ Found {} jobs", jobs.len());

            if !jobs.is_empty() {
                // Display first 10 jobs
                println!("\nTop results:");
                for (i, job) in jobs.iter().take(10).enumerate() {
                    println!(
                        "  {}. {} at {} ({})",
                        i + 1,
                        job.title,
                        job.company,
                        job.location
                    );
                }

                // Save results
                let timestamp = chrono::Local::now().format("%Y%m%d_%H%M%S");
                let filename = format!("job_search_{timestamp}.toml");
                let path = manager.save_results(&jobs, &filename)?;
                println!("\n✓ Results saved to: {}", path.display());

                // Ask if user wants to export to job descriptions
                print!("\nExport jobs to job descriptions folder? (y/n): ");
                io::stdout().flush().unwrap();
                let mut export = String::new();
                io::stdin().read_line(&mut export).unwrap();

                if export.trim().to_lowercase() == "y" {
                    let exported = export_jobs_to_descriptions(&jobs, results_folder)?;
                    println!("✓ Exported {exported} jobs to job descriptions folder");
                }
            }
        }
        Err(e) => {
            eprintln!("\n✗ Job search failed: {e}");
        }
    }

    Ok(())
}

fn view_saved_searches(saved_searches_path: &PathBuf) -> Result<()> {
    let manager = SavedSearchManager::new(saved_searches_path)?;
    let searches = manager.list();

    if searches.is_empty() {
        println!("\nNo saved searches found.");
    } else {
        println!("\nSaved searches:");
        for (i, name) in searches.iter().enumerate() {
            if let Some(search) = manager.get(name) {
                let keywords = search
                    .filters
                    .keywords
                    .as_ref()
                    .map_or("(none)", |k| k.as_str());
                let last_run = search.last_run.as_ref().map_or("Never", |d| d.as_str());
                println!(
                    "  {}. {} (keywords: {}, last run: {})",
                    i + 1,
                    name,
                    keywords,
                    last_run
                );
            }
        }
    }

    Ok(())
}

async fn run_saved_search(results_folder: &PathBuf, saved_searches_path: &PathBuf) -> Result<()> {
    let manager = SavedSearchManager::new(saved_searches_path)?;
    let searches = manager.list();

    if searches.is_empty() {
        println!("\nNo saved searches found.");
        return Ok(());
    }

    println!("\nSelect saved search to run:");
    for (i, name) in searches.iter().enumerate() {
        println!("  {}. {}", i + 1, name);
    }
    println!("  0. Cancel");

    print!("\nEnter choice: ");
    io::stdout().flush().unwrap();

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();

    if let Ok(num) = input.trim().parse::<usize>() {
        if num == 0 {
            return Ok(());
        }
        if let Some(name) = searches.get(num - 1) {
            println!("\nRunning saved search: {name}...");

            // Get the saved search and run it
            if let Some(saved_search) = manager.get(name) {
                let mut scraper_manager =
                    JobScraperManager::new(results_folder, saved_searches_path)?;

                // Register available scrapers
                let sources = vec!["linkedin", "indeed", "glassdoor", "google", "ziprecruiter"];
                let retry_config = RetryConfig::default();
                let cache_config = CacheConfig::default();

                for source in &sources {
                    if let Ok(scraper) = JobSpyScraper::new(source) {
                        if scraper.check_dependencies().is_ok() {
                            let retry_scraper = RetryWrapper::new(scraper, retry_config.clone());
                            let cached_scraper =
                                CacheWrapper::new(retry_scraper, cache_config.clone());
                            scraper_manager.register_scraper(Box::new(cached_scraper));
                        }
                    }
                }

                let available_scrapers = scraper_manager.available_sources();
                if available_scrapers.is_empty() {
                    println!("\n⚠ No scrapers available.");
                    return Ok(());
                }

                match scraper_manager
                    .search_jobs(&saved_search.filters, &available_scrapers, 50)
                    .await
                {
                    Ok(jobs) => {
                        println!("\n✓ Found {} jobs", jobs.len());
                        // Update last run timestamp
                        let mut manager = SavedSearchManager::new(saved_searches_path)?;
                        manager.update_last_run(name)?;
                    }
                    Err(e) => {
                        eprintln!("\n✗ Search failed: {e}");
                    }
                }
            }
        }
    }

    Ok(())
}

fn create_saved_search(saved_searches_path: &PathBuf) -> Result<()> {
    print!("\nEnter search name: ");
    io::stdout().flush().unwrap();
    let mut name = String::new();
    io::stdin().read_line(&mut name).unwrap();
    let name = name.trim();

    if name.is_empty() {
        println!("Search name cannot be empty.");
        return Ok(());
    }

    print!("Enter keywords: ");
    io::stdout().flush().unwrap();
    let mut keywords = String::new();
    io::stdin().read_line(&mut keywords).unwrap();

    print!("Enter location (optional): ");
    io::stdout().flush().unwrap();
    let mut location = String::new();
    io::stdin().read_line(&mut location).unwrap();

    print!("Remote only? (y/n): ");
    io::stdout().flush().unwrap();
    let mut remote = String::new();
    io::stdin().read_line(&mut remote).unwrap();
    let remote_only = remote.trim().to_lowercase() == "y";

    let mut filters = SearchFilters::default();
    if !keywords.trim().is_empty() {
        filters.keywords = Some(keywords.trim().to_string());
    }
    if !location.trim().is_empty() {
        filters.location = Some(location.trim().to_string());
    }
    filters.remote_only = remote_only;

    let search = SavedSearch::new(
        name,
        filters,
        vec!["linkedin".to_string(), "indeed".to_string()],
    );

    let mut manager = SavedSearchManager::new(saved_searches_path)?;
    manager.save(search)?;

    println!("\n✓ Saved search '{name}' created successfully.");

    Ok(())
}

fn delete_saved_search(saved_searches_path: &PathBuf) -> Result<()> {
    let manager = SavedSearchManager::new(saved_searches_path)?;
    let searches = manager.list();

    if searches.is_empty() {
        println!("\nNo saved searches found.");
        return Ok(());
    }

    println!("\nSelect saved search to delete:");
    for (i, name) in searches.iter().enumerate() {
        println!("  {}. {}", i + 1, name);
    }
    println!("  0. Cancel");

    print!("\nEnter choice: ");
    io::stdout().flush().unwrap();

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();

    if let Ok(num) = input.trim().parse::<usize>() {
        if num == 0 {
            return Ok(());
        }
        if let Some(name) = searches.get(num - 1) {
            print!("\nAre you sure you want to delete '{name}'? (y/n): ");
            io::stdout().flush().unwrap();

            let mut confirm = String::new();
            io::stdin().read_line(&mut confirm).unwrap();

            if confirm.trim().to_lowercase() == "y" {
                let mut manager = SavedSearchManager::new(saved_searches_path)?;
                manager.delete(name)?;
                println!("\n✓ Saved search '{name}' deleted.");
            }
        }
    }

    Ok(())
}

fn export_jobs_to_descriptions(
    jobs: &[crate::scraper::JobPosting],
    folder: &PathBuf,
) -> Result<i32> {
    use std::fs;
    use std::io::Write;

    fs::create_dir_all(folder)?;
    let mut count = 0;

    for job in jobs {
        let filename = format!(
            "{}_{}.txt",
            sanitize_filename(&job.company),
            sanitize_filename(&job.title)
        );
        let filepath = folder.join(&filename);

        let content = format!(
            "Title: {}\nCompany: {}\nLocation: {}\nSource: {}\nURL: {}\n\nDescription:\n{}\n",
            job.title, job.company, job.location, job.source, job.url, job.description
        );

        let mut file = fs::File::create(&filepath)?;
        file.write_all(content.as_bytes())?;
        count += 1;
    }

    Ok(count)
}

// -------------------------
// View Files Menu
// -------------------------

fn view_files_menu(config: &Config) {
    println!("\n{}", "-".repeat(60));
    println!("AVAILABLE FILES");
    println!("{}", "-".repeat(60));

    let input_handler = InputHandler::new(
        config.input_resumes_folder.clone(),
        config.job_descriptions_folder.clone(),
    );

    // List resumes
    println!("\nResumes in {}:", config.input_resumes_folder.display());
    match input_handler.list_resumes() {
        Ok(files) => {
            if files.is_empty() {
                println!("  (no files found)");
            } else {
                for (i, file) in files.iter().enumerate() {
                    println!("  {}. {}", i + 1, file.display());
                }
            }
        }
        Err(e) => {
            eprintln!("  Error: {e}");
        }
    }

    // List job descriptions
    println!(
        "\nJob descriptions in {}:",
        config.job_descriptions_folder.display()
    );
    match std::fs::read_dir(&config.job_descriptions_folder) {
        Ok(entries) => {
            let files: Vec<_> = entries.filter_map(std::result::Result::ok).collect();
            if files.is_empty() {
                println!("  (no files found)");
            } else {
                for (i, entry) in files.iter().enumerate() {
                    println!("  {}. {}", i + 1, entry.path().display());
                }
            }
        }
        Err(e) => {
            eprintln!("  Error: {e}");
        }
    }
}

// -------------------------
// View Configuration
// -------------------------

fn view_config(config: &Config) {
    println!("\n{}", "=".repeat(60));
    println!("CONFIGURATION");
    println!("{}", "=".repeat(60));
    println!("\nPaths:");
    println!("  Input resumes: {}", config.input_resumes_folder.display());
    println!(
        "  Job descriptions: {}",
        config.job_descriptions_folder.display()
    );
    println!("  Output: {}", config.output_folder.display());
    println!("  State file: {}", config.state_file.display());
    println!(
        "  Scoring weights: {}",
        config.scoring_weights_file.display()
    );

    println!("\nProcessing:");
    println!("  Versions per job: {}", config.num_versions_per_job);
    println!(
        "  Iterate until score reached: {}",
        config.iterate_until_score_reached
    );
    println!("  Target score: {:.2}", config.target_score);
    println!("  Max iterations: {}", config.max_iterations);
    println!("  Iteration strategy: {}", config.iteration_strategy);

    println!("\nOutput:");
    println!("  Format: {}", config.structured_output_format);
    println!("  Subdirectory pattern: {}", config.output_subdir_pattern);

    println!("\nRecommendations:");
    println!("  Enabled: {}", config.recommendations_enabled);
    println!("  Max items: {}", config.recommendations_max_items);

    println!("\nValidation:");
    println!("  Schema validation: {}", config.schema_validation_enabled);
    println!("{}", "=".repeat(60));
}

// -------------------------
// View State
// -------------------------

fn view_state(config: &Config) -> Result<()> {
    println!("\n{}", "=".repeat(60));
    println!("PROCESSED RESUMES STATE");
    println!("{}", "=".repeat(60));

    let state_manager = StateManager::new(config.state_file.clone())?;
    let hashes = state_manager.list_all_hashes();

    if hashes.is_empty() {
        println!("\nNo resumes have been processed yet.");
    } else {
        println!("\nTotal processed: {}", hashes.len());
        println!("\nRecent entries (last 10):");
        for (i, hash) in hashes.iter().rev().take(10).enumerate() {
            if let Some(state) = state_manager.get_resume_state(hash) {
                println!("  {}. {} -> {}", i + 1, &hash[0..12], state.output_path);
            }
        }
    }

    println!("{}", "=".repeat(60));
    Ok(())
}

// -------------------------
// View Outputs Menu
// -------------------------

fn view_outputs_menu(config: &Config) {
    println!("\n{}", "-".repeat(60));
    println!("OUTPUT DIRECTORIES");
    println!("{}", "-".repeat(60));

    match std::fs::read_dir(&config.output_folder) {
        Ok(entries) => {
            let dirs: Vec<_> = entries
                .filter_map(std::result::Result::ok)
                .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
                .collect();

            if dirs.is_empty() {
                println!("\nNo output directories found.");
            } else {
                println!("\nAvailable outputs:");
                for (i, dir) in dirs.iter().enumerate() {
                    let path = dir.path();
                    let count = count_files_in_dir(&path);
                    println!("  {}. {} ({} files)", i + 1, path.display(), count);
                }

                println!("\nEnter number to view details (0 to cancel):");
                print!("Choice: ");
                io::stdout().flush().unwrap();

                let mut input = String::new();
                io::stdin().read_line(&mut input).unwrap();

                if let Ok(num) = input.trim().parse::<usize>() {
                    if num > 0 && num <= dirs.len() {
                        let selected = &dirs[num - 1].path();
                        view_output_directory(selected);
                    }
                }
            }
        }
        Err(e) => {
            eprintln!("Error reading output folder: {e}");
        }
    }
}

fn count_files_in_dir(path: &PathBuf) -> usize {
    std::fs::read_dir(path)
        .map(|entries| entries.filter_map(std::result::Result::ok).count())
        .unwrap_or(0)
}

fn view_output_directory(path: &PathBuf) {
    println!("\n{}", "-".repeat(60));
    println!("Contents of: {}", path.display());
    println!("{}", "-".repeat(60));

    match std::fs::read_dir(path) {
        Ok(entries) => {
            for entry in entries.filter_map(std::result::Result::ok) {
                let metadata = entry.metadata().unwrap();
                let size = metadata.len();
                let size_str = if size < 1024 {
                    format!("{size} B")
                } else if size < 1024 * 1024 {
                    format!("{:.1} KB", size as f64 / 1024.0)
                } else {
                    format!("{:.1} MB", size as f64 / (1024.0 * 1024.0))
                };

                println!(
                    "  {} ({}, {})",
                    entry.file_name().to_string_lossy(),
                    if metadata.is_dir() { "dir" } else { "file" },
                    size_str
                );
            }
        }
        Err(e) => {
            eprintln!("Error: {e}");
        }
    }
}

// -------------------------
// Settings Menu
// -------------------------

fn settings_menu(config: &Config) {
    println!("\n{}", "-".repeat(60));
    println!("SETTINGS");
    println!("{}", "-".repeat(60));
    println!("1. View current settings");
    println!("2. Edit target score");
    println!("3. Edit max iterations");
    println!("4. Toggle recommendations");
    println!("5. Toggle schema validation");
    println!("0. Back to main menu");
    println!("{}", "-".repeat(60));
    println!("\nNote: Settings are not persisted in this session.");
    println!("To make permanent changes, edit config/config.toml");

    print!("\nEnter your choice: ");
    io::stdout().flush().unwrap();

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();
    let choice = input.trim();

    match choice {
        "1" => {
            view_config(config);
        }
        "2" => {
            println!("\nCurrent target score: {:.2}", config.target_score);
            print!("Enter new target score (0-100): ");
            io::stdout().flush().unwrap();

            let mut new_score = String::new();
            io::stdin().read_line(&mut new_score).unwrap();

            if let Ok(score) = new_score.trim().parse::<f64>() {
                if (0.0..=100.0).contains(&score) {
                    println!("Target score would be set to: {score:.2}");
                    println!("(Note: Changes not persisted - edit config.toml to save)");
                } else {
                    println!("Invalid score. Must be between 0 and 100.");
                }
            }
        }
        "3" => {
            println!("\nCurrent max iterations: {}", config.max_iterations);
            print!("Enter new max iterations: ");
            io::stdout().flush().unwrap();

            let mut new_iter = String::new();
            io::stdin().read_line(&mut new_iter).unwrap();

            if let Ok(iter) = new_iter.trim().parse::<i32>() {
                if iter > 0 {
                    println!("Max iterations would be set to: {iter}");
                    println!("(Note: Changes not persisted - edit config.toml to save)");
                } else {
                    println!("Invalid value. Must be greater than 0.");
                }
            }
        }
        "4" => {
            println!(
                "\nRecommendations are currently: {}",
                if config.recommendations_enabled {
                    "enabled"
                } else {
                    "disabled"
                }
            );
            println!("Toggle? (y/n): ");
            io::stdout().flush().unwrap();

            let mut toggle = String::new();
            io::stdin().read_line(&mut toggle).unwrap();

            if toggle.trim().to_lowercase() == "y" {
                let new_state = !config.recommendations_enabled;
                println!(
                    "Recommendations would be: {}",
                    if new_state { "enabled" } else { "disabled" }
                );
                println!("(Note: Changes not persisted - edit config.toml to save)");
            }
        }
        "5" => {
            println!(
                "\nSchema validation is currently: {}",
                if config.schema_validation_enabled {
                    "enabled"
                } else {
                    "disabled"
                }
            );
            println!("Toggle? (y/n): ");
            io::stdout().flush().unwrap();

            let mut toggle = String::new();
            io::stdin().read_line(&mut toggle).unwrap();

            if toggle.trim().to_lowercase() == "y" {
                let new_state = !config.schema_validation_enabled;
                println!(
                    "Schema validation would be: {}",
                    if new_state { "enabled" } else { "disabled" }
                );
                println!("(Note: Changes not persisted - edit config.toml to save)");
            }
        }
        "0" => {}
        _ => {
            println!("Invalid choice.");
        }
    }
}

// -------------------------
// Test OCR Menu
// -------------------------

fn test_ocr_menu() {
    println!("\n{}", "-".repeat(60));
    println!("TEST OCR (Optical Character Recognition)");
    println!("{}", "-".repeat(60));

    // Check if Tesseract is installed
    match check_tesseract_installed() {
        Ok(()) => {
            println!("✓ Tesseract OCR is installed and available");
        }
        Err(e) => {
            println!("✗ Tesseract OCR is not available: {e}");
            println!("\nTo use OCR features, please install Tesseract:");
            println!("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki");
            println!("  macOS: brew install tesseract");
            println!("  Linux: sudo apt-get install tesseract-ocr");
            return;
        }
    }

    print!("\nEnter path to image file (PNG, JPG, TIFF, BMP): ");
    io::stdout().flush().unwrap();

    let mut image_path = String::new();
    io::stdin().read_line(&mut image_path).unwrap();
    let image_path = image_path.trim();

    if image_path.is_empty() {
        println!("No path provided.");
        return;
    }

    let path = PathBuf::from(image_path);
    if !path.exists() {
        println!("File not found: {}", path.display());
        return;
    }

    print!("Enter language code (default: eng): ");
    io::stdout().flush().unwrap();

    let mut lang = String::new();
    io::stdin().read_line(&mut lang).unwrap();
    let lang = if lang.trim().is_empty() {
        None
    } else {
        Some(lang.trim())
    };

    println!("\nExtracting text from image...");
    match extract_text_from_image(&path, lang) {
        Ok(text) => {
            println!("\n{}", "=".repeat(60));
            println!("EXTRACTED TEXT");
            println!("{}", "=".repeat(60));
            println!("{text}");
            println!("{}", "=".repeat(60));
            println!("\n✓ Text extraction successful!");
            println!("  Characters extracted: {}", text.len());
            println!("  Words extracted: {}", text.split_whitespace().count());
        }
        Err(e) => {
            eprintln!("\n✗ Text extraction failed: {e}");
        }
    }
}

// -------------------------
// View History
// -------------------------

fn view_history(history: &OperationHistory) {
    println!("\n{}", "-".repeat(60));
    println!("RECENT OPERATIONS");
    println!("{}", "-".repeat(60));

    if history.is_empty() {
        println!("\nNo operations recorded yet.");
    } else {
        println!();
        for (i, op) in history.recent(10).iter().enumerate() {
            println!("  {}. {}", i + 1, op);
        }
    }

    println!("{}", "-".repeat(60));
}

// -------------------------
// Check API Keys Menu
// -------------------------

/// Check and display status of all API keys.
fn check_api_keys_menu() {
    println!("\n{}", "-".repeat(60));
    println!("API KEYS STATUS");
    println!("{}", "-".repeat(60));

    let keys = [
        ("GEMINI_API_KEY", "Google Gemini"),
        ("OPENAI_API_KEY", "OpenAI"),
        ("ANTHROPIC_API_KEY", "Anthropic Claude"),
        ("OLLAMA_HOST", "Ollama (optional)"),
    ];

    let mut found_count = 0;
    let mut missing_count = 0;

    println!();
    for (env_var, name) in &keys {
        match std::env::var(env_var) {
            Ok(value) => {
                let masked = if value.len() > 8 {
                    format!("{}...{}", &value[..4], &value[value.len() - 4..])
                } else {
                    "****".to_string()
                };
                println!("  [✓] {name}: {masked}");
                found_count += 1;
            }
            Err(_) => {
                if *env_var == "OLLAMA_HOST" {
                    println!("  [○] {name}: Not set (will use default: http://localhost:11434)");
                } else {
                    println!("  [✗] {name}: Not found");
                    missing_count += 1;
                }
            }
        }
    }

    println!();
    println!("Summary: {found_count} found, {missing_count} missing");
    println!("{}", "-".repeat(60));

    if missing_count > 0 {
        println!("\nTo set environment variables on Windows:");
        println!("  Command Prompt: set KEY_NAME=your_key_value");
        println!("  PowerShell:     $env:KEY_NAME=\"your_key_value\"");
        println!("\nFor permanent setup, use System Properties → Environment Variables");
    }
}

// -------------------------
// JobSpy Setup Menu
// -------------------------

/// Check and setup `JobSpy` dependencies.
fn jobspy_setup_menu() {
    use crate::scraper::setup::{run_auto_setup, show_dependency_status};

    println!("\n{}", "-".repeat(60));
    println!("JobSpy Setup");
    println!("{}", "-".repeat(60));

    // First show current status
    show_dependency_status();

    // Ask if user wants to attempt auto-setup
    println!("\nWould you like to check and install missing dependencies? [Y/n] ");
    std::io::Write::flush(&mut std::io::stdout()).ok();

    let mut input = String::new();
    std::io::stdin().read_line(&mut input).ok();

    if input.trim().is_empty() || input.trim().to_lowercase() == "y" {
        println!();
        match run_auto_setup() {
            Ok(()) => {
                println!("\n✓ JobSpy setup complete!");
                println!("You can now use job search functionality.");
            }
            Err(e) => {
                eprintln!("\n✗ Setup failed: {e}");
                println!("\nPlease try manual installation:");
                println!("  pip install python-jobspy pandas");
            }
        }
    }
}
