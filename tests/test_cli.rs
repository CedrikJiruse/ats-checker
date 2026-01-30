//! Integration tests for CLI argument parsing.

mod common;

use ats_checker::cli::{Cli, Commands};
use clap::Parser;

#[test]
fn test_cli_score_resume_command() {
    let args = vec![
        "ats-checker",
        "score-resume",
        "--resume",
        "test.toml",
        "--weights",
        "weights.toml",
    ];

    let cli = Cli::try_parse_from(args).unwrap();

    match cli.command {
        Some(Commands::ScoreResume { resume, weights, .. }) => {
            assert_eq!(resume, "test.toml");
            assert_eq!(weights.unwrap(), "weights.toml");
        }
        _ => panic!("Expected ScoreResume command"),
    }
}

#[test]
fn test_cli_score_match_command() {
    let args = vec![
        "ats-checker",
        "score-match",
        "--resume",
        "resume.toml",
        "--job",
        "job.txt",
    ];

    let cli = Cli::try_parse_from(args).unwrap();

    match cli.command {
        Some(Commands::ScoreMatch { resume, job, .. }) => {
            assert_eq!(resume, "resume.toml");
            assert_eq!(job, "job.txt");
        }
        _ => panic!("Expected ScoreMatch command"),
    }
}

#[test]
fn test_cli_rank_jobs_command() {
    let args = vec![
        "ats-checker",
        "rank-jobs",
        "--results",
        "results.toml",
        "--top",
        "10",
    ];

    let cli = Cli::try_parse_from(args).unwrap();

    match cli.command {
        Some(Commands::RankJobs { results, top, .. }) => {
            assert_eq!(results, "results.toml");
            assert_eq!(top, 10);
        }
        _ => panic!("Expected RankJobs command"),
    }
}

#[test]
fn test_cli_default_config_path() {
    let args = vec!["ats-checker"];

    let cli = Cli::try_parse_from(args).unwrap();

    // Default config should be "config/config.toml"
    assert_eq!(cli.config, "config/config.toml");
}

#[test]
fn test_cli_custom_config_path() {
    let args = vec!["ats-checker", "--config", "my_config.toml"];

    let cli = Cli::try_parse_from(args).unwrap();

    assert_eq!(cli.config, "my_config.toml");
}

#[test]
fn test_cli_verbose_flag() {
    let args = vec!["ats-checker", "--verbose"];

    let cli = Cli::try_parse_from(args).unwrap();

    assert!(cli.verbose);
}

#[test]
fn test_cli_quiet_flag() {
    let args = vec!["ats-checker", "--quiet"];

    let cli = Cli::try_parse_from(args).unwrap();

    assert!(cli.quiet);
}

#[test]
fn test_cli_no_command_is_interactive() {
    let args = vec!["ats-checker"];

    let cli = Cli::try_parse_from(args).unwrap();

    // No command means interactive mode
    assert!(cli.command.is_none());
}

#[test]
fn test_cli_score_resume_with_verbose() {
    let args = vec![
        "ats-checker",
        "--verbose",
        "score-resume",
        "--resume",
        "test.toml",
    ];

    let cli = Cli::try_parse_from(args).unwrap();

    assert!(cli.verbose);
    match cli.command {
        Some(Commands::ScoreResume { resume, .. }) => {
            assert_eq!(resume, "test.toml");
        }
        _ => panic!("Expected ScoreResume command"),
    }
}

#[test]
fn test_cli_rank_jobs_default_top() {
    let args = vec!["ats-checker", "rank-jobs", "--results", "results.toml"];

    let cli = Cli::try_parse_from(args).unwrap();

    match cli.command {
        Some(Commands::RankJobs { top, .. }) => {
            // Default value is 20
            assert_eq!(top, 20);
        }
        _ => panic!("Expected RankJobs command"),
    }
}
