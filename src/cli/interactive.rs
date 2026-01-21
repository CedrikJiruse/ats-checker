//! Interactive menu for CLI.

use crate::config::Config;
use crate::error::Result;
use crate::input::InputHandler;
use crate::processor::ResumeProcessor;
use crate::scraper::JobScraperManager;
use crate::state::StateManager;
use std::io::{self, Write};

// -------------------------
// Main Interactive Menu
// -------------------------

/// Run the interactive menu.
pub async fn run_interactive_menu(config: Config) -> Result<()> {
    println!("\n{}", "=".repeat(60));
    println!("ATS RESUME CHECKER - Interactive Mode");
    println!("{}", "=".repeat(60));

    loop {
        println!("\n{}", "-".repeat(60));
        println!("MAIN MENU");
        println!("{}", "-".repeat(60));
        println!("1. Process resumes");
        println!("2. Job search");
        println!("3. View available files");
        println!("4. View configuration");
        println!("5. View state (processed resumes)");
        println!("0. Exit");
        println!("{}", "-".repeat(60));

        print!("\nEnter your choice: ");
        io::stdout().flush().unwrap();

        let mut input = String::new();
        io::stdin().read_line(&mut input).unwrap();
        let choice = input.trim();

        match choice {
            "1" => {
                if let Err(e) = process_resumes_menu(&config).await {
                    eprintln!("Error: {}", e);
                }
            }
            "2" => {
                if let Err(e) = job_search_menu(&config).await {
                    eprintln!("Error: {}", e);
                }
            }
            "3" => {
                if let Err(e) = view_files_menu(&config) {
                    eprintln!("Error: {}", e);
                }
            }
            "4" => {
                view_config(&config);
            }
            "5" => {
                if let Err(e) = view_state(&config) {
                    eprintln!("Error: {}", e);
                }
            }
            "0" => {
                println!("\nExiting. Goodbye!");
                break;
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
            println!("Total: {} | Successful: {} | Failed: {}", results.len(), successful, failed);

            if failed > 0 {
                println!("\nFailed resumes:");
                for result in results.iter().filter(|r| !r.success) {
                    if let Some(err) = &result.error {
                        println!("  - {}", err);
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

            println!("\nProcessing {}...", resume_path);
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

            println!("\nProcessing {} with job {}...", resume_path, job_path);
            let result = processor.process_resume(resume_path, Some(job_path)).await?;

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
        "0" => {}
        _ => {
            println!("Invalid choice.");
        }
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
    println!("0. Back to main menu");
    println!("{}", "-".repeat(60));

    print!("\nEnter your choice: ");
    io::stdout().flush().unwrap();

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();
    let choice = input.trim();

    match choice {
        "1" => {
            println!("\nJob search feature coming soon!");
            println!("This will allow you to search job boards and save results.");
        }
        "2" => {
            println!("\nSaved searches feature coming soon!");
        }
        "0" => {}
        _ => {
            println!("Invalid choice.");
        }
    }

    Ok(())
}

// -------------------------
// View Files Menu
// -------------------------

fn view_files_menu(config: &Config) -> Result<()> {
    println!("\n{}", "-".repeat(60));
    println!("AVAILABLE FILES");
    println!("{}", "-".repeat(60));

    let input_handler = InputHandler::new(
        config.input_resumes_folder.clone(),
        config.job_descriptions_folder.clone(),
        config.tesseract_cmd.clone(),
    );

    // List resumes
    println!("\nResumes in {}:", config.input_resumes_folder.display());
    match input_handler.list_files() {
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
            eprintln!("  Error: {}", e);
        }
    }

    // List job descriptions
    println!("\nJob descriptions in {}:", config.job_descriptions_folder.display());
    match std::fs::read_dir(&config.job_descriptions_folder) {
        Ok(entries) => {
            let files: Vec<_> = entries.filter_map(|e| e.ok()).collect();
            if files.is_empty() {
                println!("  (no files found)");
            } else {
                for (i, entry) in files.iter().enumerate() {
                    println!("  {}. {}", i + 1, entry.path().display());
                }
            }
        }
        Err(e) => {
            eprintln!("  Error: {}", e);
        }
    }

    Ok(())
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
    println!("  Job descriptions: {}", config.job_descriptions_folder.display());
    println!("  Output: {}", config.output_folder.display());
    println!("  State file: {}", config.state_file.display());
    println!("  Scoring weights: {}", config.scoring_weights_file.display());

    println!("\nProcessing:");
    println!("  Versions per job: {}", config.num_versions_per_job);
    println!("  Iterate until score reached: {}", config.iterate_until_score_reached);
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
