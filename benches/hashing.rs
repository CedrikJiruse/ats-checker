//! Benchmarks for file hashing operations.

use ats_checker::utils::hash::{calculate_bytes_hash, calculate_string_hash};
use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

fn bench_string_hashing(c: &mut Criterion) {
    let mut group = c.benchmark_group("string_hashing");

    for size in [100, 1_000, 10_000, 100_000] {
        let data = "x".repeat(size);

        group.throughput(Throughput::Bytes(size as u64));
        group.bench_with_input(BenchmarkId::from_parameter(size), &data, |b, data| {
            b.iter(|| calculate_string_hash(black_box(data)));
        });
    }

    group.finish();
}

fn bench_bytes_hashing(c: &mut Criterion) {
    let mut group = c.benchmark_group("bytes_hashing");

    for size in [100, 1_000, 10_000, 100_000] {
        let data = vec![0u8; size];

        group.throughput(Throughput::Bytes(size as u64));
        group.bench_with_input(BenchmarkId::from_parameter(size), &data, |b, data| {
            b.iter(|| calculate_bytes_hash(black_box(data)));
        });
    }

    group.finish();
}

criterion_group!(benches, bench_string_hashing, bench_bytes_hashing);
criterion_main!(benches);
