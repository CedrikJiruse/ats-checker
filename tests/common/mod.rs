//! Common test utilities and helpers.

#![allow(dead_code)]

use std::path::{Path, PathBuf};
use tempfile::TempDir;

/// Create a temporary directory for tests.
pub fn create_temp_dir() -> TempDir {
    TempDir::new().expect("Failed to create temp directory")
}

/// Create a test file with the given content.
pub fn create_test_file(dir: &Path, name: &str, content: &str) -> PathBuf {
    let file_path = dir.join(name);
    std::fs::write(&file_path, content).expect("Failed to write test file");
    file_path
}

/// Sample resume text for testing.
pub fn sample_resume_text() -> &'static str {
    r#"
John Doe
Software Engineer
john.doe@example.com
(555) 123-4567

SUMMARY
Experienced software engineer with 5+ years of experience in full-stack development.

EXPERIENCE
Senior Software Engineer | Tech Corp | 2020-Present
- Developed microservices architecture handling 1M+ requests/day
- Led team of 5 engineers in agile development
- Reduced system latency by 40% through optimization

Software Engineer | StartUp Inc | 2018-2020
- Built RESTful APIs using Python and Flask
- Implemented CI/CD pipelines with Jenkins
- Collaborated with cross-functional teams

EDUCATION
B.S. Computer Science | University of Technology | 2018
GPA: 3.8/4.0

SKILLS
Languages: Python, Rust, JavaScript, SQL
Frameworks: Django, Flask, React, Node.js
Tools: Docker, Kubernetes, Git, AWS
"#
}

/// Sample job description text for testing.
pub fn sample_job_description() -> &'static str {
    r#"
Software Engineer - Backend
Tech Company Inc.

We are seeking an experienced Backend Software Engineer to join our team.

Requirements:
- 3+ years of experience with Python or similar languages
- Experience with microservices architecture
- Strong understanding of RESTful APIs
- Experience with Docker and Kubernetes
- Bachelor's degree in Computer Science or related field

Responsibilities:
- Design and implement scalable backend services
- Collaborate with frontend and DevOps teams
- Participate in code reviews and architecture discussions
- Optimize system performance and reliability

Nice to have:
- Experience with Rust or Go
- Knowledge of cloud platforms (AWS, GCP, Azure)
- Experience with CI/CD pipelines
"#
}

/// Sample resume JSON structure for testing.
pub fn sample_resume_json() -> serde_json::Value {
    serde_json::json!({
        "personal_info": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "(555) 123-4567",
            "title": "Software Engineer"
        },
        "summary": "Experienced software engineer with 5+ years of experience in full-stack development.",
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "duration": "2020-Present",
                "bullets": [
                    "Developed microservices architecture handling 1M+ requests/day",
                    "Led team of 5 engineers in agile development",
                    "Reduced system latency by 40% through optimization"
                ]
            },
            {
                "title": "Software Engineer",
                "company": "StartUp Inc",
                "duration": "2018-2020",
                "bullets": [
                    "Built RESTful APIs using Python and Flask",
                    "Implemented CI/CD pipelines with Jenkins",
                    "Collaborated with cross-functional teams"
                ]
            }
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "University of Technology",
                "year": "2018",
                "gpa": "3.8"
            }
        ],
        "skills": {
            "languages": ["Python", "Rust", "JavaScript", "SQL"],
            "frameworks": ["Django", "Flask", "React", "Node.js"],
            "tools": ["Docker", "Kubernetes", "Git", "AWS"]
        }
    })
}

/// Sample minimal config TOML for testing.
pub fn sample_config_toml() -> &'static str {
    r#"
[paths]
input_resumes_folder = "workspace/input_resumes"
job_descriptions_folder = "workspace/job_descriptions"
output_folder = "workspace/output"
state_file = "data/test_state.toml"
scoring_weights_file = "config/scoring_weights.toml"

[processing]
num_versions_per_job = 1
iterate_until_score_reached = false
max_iterations = 3
target_score = 80.0
iteration_strategy = "best_of"
structured_output_format = "json"

[ai]
gemini_api_key_env = "GEMINI_API_KEY"
default_model_name = "gemini-1.5-flash"
default_temperature = 0.7
"#
}

/// Sample scoring weights TOML for testing.
pub fn sample_scoring_weights() -> &'static str {
    r#"
[resume]
completeness = 0.25
skills_quality = 0.25
experience_quality = 0.25
impact = 0.25

[match]
keyword_overlap = 0.4
skills_overlap = 0.3
role_alignment = 0.3

[job]
completeness = 0.4
clarity = 0.3
compensation_transparency = 0.2
link_quality = 0.1
"#
}
