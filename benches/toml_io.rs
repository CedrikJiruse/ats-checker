//! Benchmarks for TOML I/O operations.

use ats_checker::toml_io::{dumps, loads};
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use serde_json::json;

fn sample_data_small() -> serde_json::Value {
    json!({
        "name": "John Doe",
        "age": 30,
        "city": "New York"
    })
}

fn sample_data_medium() -> serde_json::Value {
    json!({
        "personal_info": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "(555) 123-4567"
        },
        "experience": [
            {
                "title": "Engineer",
                "company": "Tech Corp",
                "years": 5
            },
            {
                "title": "Developer",
                "company": "StartUp",
                "years": 3
            }
        ],
        "skills": ["Python", "Rust", "JavaScript", "Docker"]
    })
}

fn sample_data_large() -> serde_json::Value {
    let mut experience = Vec::new();
    for i in 0..20 {
        experience.push(json!({
            "title": format!("Position {}", i),
            "company": format!("Company {}", i),
            "duration": "2020-2021",
            "bullets": vec![
                "Achievement 1",
                "Achievement 2",
                "Achievement 3"
            ]
        }));
    }

    json!({
        "personal_info": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "(555) 123-4567"
        },
        "experience": experience,
        "skills": {
            "languages": ["Python", "Rust", "JavaScript", "Go", "Java"],
            "frameworks": ["Django", "Flask", "React", "Vue", "Angular"],
            "tools": ["Docker", "Kubernetes", "Git", "Jenkins", "AWS"]
        }
    })
}

fn bench_toml_dumps_small(c: &mut Criterion) {
    let data = sample_data_small();

    c.bench_function("toml_dumps_small", |b| {
        b.iter(|| dumps(black_box(&data)));
    });
}

fn bench_toml_dumps_medium(c: &mut Criterion) {
    let data = sample_data_medium();

    c.bench_function("toml_dumps_medium", |b| {
        b.iter(|| dumps(black_box(&data)));
    });
}

fn bench_toml_dumps_large(c: &mut Criterion) {
    let data = sample_data_large();

    c.bench_function("toml_dumps_large", |b| {
        b.iter(|| dumps(black_box(&data)));
    });
}

fn bench_toml_loads_small(c: &mut Criterion) {
    let data = sample_data_small();
    let toml_str = dumps(&data).unwrap();

    c.bench_function("toml_loads_small", |b| {
        b.iter(|| loads(black_box(&toml_str)));
    });
}

fn bench_toml_loads_medium(c: &mut Criterion) {
    let data = sample_data_medium();
    let toml_str = dumps(&data).unwrap();

    c.bench_function("toml_loads_medium", |b| {
        b.iter(|| loads(black_box(&toml_str)));
    });
}

criterion_group!(
    benches,
    bench_toml_dumps_small,
    bench_toml_dumps_medium,
    bench_toml_dumps_large,
    bench_toml_loads_small,
    bench_toml_loads_medium
);
criterion_main!(benches);
