//! ATS Resume Checker - Main binary.

use clap::Parser;
use ats_checker::{Config, cli::Cli};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize logging
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    // Parse CLI arguments
    let cli = Cli::parse();

    // Load configuration
    let config = Config::load(&cli.config)?;

    // Ensure directories exist
    config.ensure_directories()?;

    // Handle command
    match cli.command {
        Some(ats_checker::cli::Commands::Interactive) | None => {
            println!("Interactive mode not yet implemented");
        }
        Some(ats_checker::cli::Commands::ScoreResume { resume, weights }) => {
            println!("Scoring resume: {}", resume);
            if let Some(w) = weights {
                println!("Using weights: {}", w);
            }
        }
        Some(ats_checker::cli::Commands::ScoreMatch { resume, job, weights }) => {
            println!("Scoring match: {} vs {}", resume, job);
            if let Some(w) = weights {
                println!("Using weights: {}", w);
            }
        }
        Some(ats_checker::cli::Commands::RankJobs { results, top }) => {
            println!("Ranking jobs from: {} (top {})", results, top);
        }
    }

    Ok(())
}
