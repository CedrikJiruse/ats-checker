//! ATS Resume Checker - Main binary.

use ats_checker::cli::{handlers, interactive, Cli};
use ats_checker::Config;
use clap::Parser;
use std::process;

#[tokio::main]
async fn main() {
    // Parse CLI arguments
    let cli = Cli::parse();

    // Initialize logging based on verbosity flags
    let log_level = if cli.quiet {
        "error"
    } else if cli.verbose {
        "debug"
    } else {
        "info"
    };

    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or(log_level)).init();

    // Load configuration
    let config = match Config::load(&cli.config) {
        Ok(cfg) => cfg,
        Err(e) => {
            eprintln!("Error loading configuration: {}", e);
            process::exit(1);
        }
    };

    // Ensure directories exist
    if let Err(e) = config.ensure_directories() {
        eprintln!("Error ensuring directories exist: {}", e);
        process::exit(1);
    }

    // Handle command
    let exit_code = match cli.command {
        // Interactive mode (default)
        Some(ats_checker::cli::Commands::Interactive) | None => {
            match interactive::run_interactive_menu(config).await {
                Ok(()) => 0,
                Err(e) => {
                    eprintln!("Error in interactive mode: {}", e);
                    1
                }
            }
        }

        // Score resume subcommand
        Some(ats_checker::cli::Commands::ScoreResume { resume, weights }) => {
            match handlers::handle_score_resume(&resume, weights.as_deref(), &config) {
                Ok(code) => code,
                Err(e) => {
                    eprintln!("Error scoring resume: {}", e);
                    1
                }
            }
        }

        // Score match subcommand
        Some(ats_checker::cli::Commands::ScoreMatch {
            resume,
            job,
            weights,
        }) => match handlers::handle_score_match(&resume, &job, weights.as_deref(), &config) {
            Ok(code) => code,
            Err(e) => {
                eprintln!("Error scoring match: {}", e);
                1
            }
        },

        // Rank jobs subcommand
        Some(ats_checker::cli::Commands::RankJobs { results, top }) => {
            match handlers::handle_rank_jobs(&results, top, &config) {
                Ok(code) => code,
                Err(e) => {
                    eprintln!("Error ranking jobs: {}", e);
                    1
                }
            }
        }

        // Job search subcommand
        Some(ats_checker::cli::Commands::JobSearch {
            keywords,
            location,
            sources,
            max_results,
            remote,
            output,
        }) => {
            match handlers::handle_job_search(
                &keywords,
                location.as_deref(),
                &sources,
                max_results,
                remote,
                output.as_deref(),
                &config,
            )
            .await
            {
                Ok(code) => code,
                Err(e) => {
                    eprintln!("Error searching jobs: {}", e);
                    1
                }
            }
        }
    };

    process::exit(exit_code);
}
