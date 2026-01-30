use ats_checker::error::Result;
use ats_checker::processor::IterationStrategy;

mod common;

#[test]
fn test_iteration_strategy_from_str() -> Result<()> {
    assert!(matches!(
        "best_of".parse::<IterationStrategy>()?,
        IterationStrategy::BestOf
    ));

    assert!(matches!(
        "first_hit".parse::<IterationStrategy>()?,
        IterationStrategy::FirstHit
    ));

    assert!(matches!(
        "patience".parse::<IterationStrategy>()?,
        IterationStrategy::Patience
    ));

    Ok(())
}

#[test]
fn test_iteration_strategy_from_str_case_insensitive() -> Result<()> {
    assert!(matches!(
        "BEST_OF".parse::<IterationStrategy>()?,
        IterationStrategy::BestOf
    ));

    assert!(matches!(
        "First_Hit".parse::<IterationStrategy>()?,
        IterationStrategy::FirstHit
    ));

    assert!(matches!(
        "PaTiEnCe".parse::<IterationStrategy>()?,
        IterationStrategy::Patience
    ));

    Ok(())
}

#[test]
fn test_iteration_strategy_from_str_invalid() {
    let result = "invalid_strategy".parse::<IterationStrategy>();
    assert!(result.is_err());

    if let Err(e) = result {
        assert!(e.to_string().contains("Invalid iteration strategy"));
    }
}

#[test]
fn test_iteration_strategy_variants() {
    // Test that we can match on all variants
    let strategy = IterationStrategy::BestOf;
    match strategy {
        IterationStrategy::BestOf => {}
        _ => panic!("Expected BestOf"),
    }

    let strategy = IterationStrategy::FirstHit;
    match strategy {
        IterationStrategy::FirstHit => {}
        _ => panic!("Expected FirstHit"),
    }

    let strategy = IterationStrategy::Patience;
    match strategy {
        IterationStrategy::Patience => {}
        _ => panic!("Expected Patience"),
    }
}

#[test]
fn test_iteration_strategy_copy() {
    let strategy1 = IterationStrategy::BestOf;
    let strategy2 = strategy1; // Copy trait is used here

    assert!(matches!(strategy1, IterationStrategy::BestOf));
    assert!(matches!(strategy2, IterationStrategy::BestOf));
}

#[test]
fn test_iteration_strategy_debug() {
    let strategy = IterationStrategy::FirstHit;
    let debug_str = format!("{:?}", strategy);
    assert!(debug_str.contains("FirstHit"));
}

#[test]
fn test_iteration_strategy_equality() {
    assert_eq!(IterationStrategy::BestOf, IterationStrategy::BestOf);
    assert_eq!(IterationStrategy::FirstHit, IterationStrategy::FirstHit);
    assert_eq!(IterationStrategy::Patience, IterationStrategy::Patience);

    assert_ne!(IterationStrategy::BestOf, IterationStrategy::FirstHit);
    assert_ne!(IterationStrategy::FirstHit, IterationStrategy::Patience);
    assert_ne!(IterationStrategy::Patience, IterationStrategy::BestOf);
}

#[test]
fn test_iteration_strategy_all_variants() {
    // Ensure we can create all strategy variants
    let best_of = IterationStrategy::BestOf;
    let first_hit = IterationStrategy::FirstHit;
    let patience = IterationStrategy::Patience;

    // Verify each variant is distinct
    assert_ne!(best_of, first_hit);
    assert_ne!(first_hit, patience);
    assert_ne!(patience, best_of);
}
