//! CLI module for command-line interface.

use clap::{Parser, Subcommand};

/// ATS Resume Checker CLI.
#[derive(Parser, Debug)]
#[command(name = "ats-checker")]
#[command(about = "ATS Resume Checker - Enhance resumes using AI", long_about = None)]
pub struct Cli {
    /// Path to configuration file.
    #[arg(short, long, default_value = "config/config.toml")]
    pub config: String,

    /// Subcommand to run.
    #[command(subcommand)]
    pub command: Option<Commands>,
}

/// Available commands.
#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Interactive menu mode (default).
    Interactive,

    /// Score a resume.
    ScoreResume {
        /// Path to the resume file.
        #[arg(long)]
        resume: String,

        /// Path to scoring weights.
        #[arg(long)]
        weights: Option<String>,
    },

    /// Score resume-job match.
    ScoreMatch {
        /// Path to the resume file.
        #[arg(long)]
        resume: String,

        /// Path to the job description.
        #[arg(long)]
        job: String,

        /// Path to scoring weights.
        #[arg(long)]
        weights: Option<String>,
    },

    /// Rank jobs in a results file.
    RankJobs {
        /// Path to results file.
        #[arg(long)]
        results: String,

        /// Number of top results to show.
        #[arg(long, default_value = "20")]
        top: i32,
    },
}
