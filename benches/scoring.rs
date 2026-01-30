//! Benchmarks for scoring operations.

use ats_checker::scoring::{score_job, score_match, score_resume};
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use serde_json::json;

fn sample_resume() -> serde_json::Value {
    json!({
        "personal_info": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "(555) 123-4567",
            "title": "Software Engineer"
        },
        "summary": "Experienced software engineer with 5+ years in full-stack development.",
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "duration": "2020-Present",
                "bullets": [
                    "Developed microservices handling 1M+ requests/day",
                    "Led team of 5 engineers",
                    "Reduced latency by 40%"
                ]
            },
            {
                "title": "Software Engineer",
                "company": "StartUp Inc",
                "duration": "2018-2020",
                "bullets": [
                    "Built RESTful APIs using Python",
                    "Implemented CI/CD pipelines",
                    "Collaborated with teams"
                ]
            }
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "University",
                "year": "2018"
            }
        ],
        "skills": {
            "languages": ["Python", "Rust", "JavaScript"],
            "frameworks": ["Django", "Flask", "React"],
            "tools": ["Docker", "Kubernetes", "Git"]
        }
    })
}

fn sample_job() -> serde_json::Value {
    json!({
        "title": "Senior Software Engineer",
        "company": "Tech Company",
        "description": "We are seeking an experienced software engineer with expertise in Python, \
                       microservices, Docker, and Kubernetes. Must have 3+ years experience.",
        "requirements": ["Python", "Docker", "Kubernetes", "Microservices"],
        "salary": "$120,000 - $180,000"
    })
}

fn bench_resume_scoring(c: &mut Criterion) {
    let resume = sample_resume();

    c.bench_function("score_resume", |b| {
        b.iter(|| score_resume(black_box(&resume), None));
    });
}

fn bench_job_scoring(c: &mut Criterion) {
    let job = sample_job();

    c.bench_function("score_job", |b| {
        b.iter(|| score_job(black_box(&job), None));
    });
}

fn bench_match_scoring(c: &mut Criterion) {
    let resume = sample_resume();
    let job = sample_job();

    c.bench_function("score_match", |b| {
        b.iter(|| score_match(black_box(&resume), black_box(&job), None));
    });
}

criterion_group!(benches, bench_resume_scoring, bench_job_scoring, bench_match_scoring);
criterion_main!(benches);
