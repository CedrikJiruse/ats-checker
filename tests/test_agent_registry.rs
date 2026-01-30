use ats_checker::agents::{AgentConfig, AgentDefaults, AgentRegistry, SyncAgentRegistry};
use ats_checker::error::Result;
use std::collections::HashMap;

mod common;

#[test]
fn test_agent_registry_creation() {
    let registry = AgentRegistry::new();
    assert_eq!(registry.list().len(), 0);
}

#[test]
fn test_agent_registry_default() {
    let registry = AgentRegistry::default();
    assert_eq!(registry.list().len(), 0);
}

#[test]
fn test_agent_registry_get_nonexistent() {
    let registry = AgentRegistry::new();
    let result = registry.get("nonexistent");
    assert!(result.is_err());

    if let Err(e) = result {
        assert!(e.to_string().contains("not found"));
    }
}

#[test]
fn test_agent_registry_from_config_empty() -> Result<()> {
    let agent_configs = HashMap::new();
    let registry = AgentRegistry::from_config(&agent_configs)?;
    assert_eq!(registry.list().len(), 0);
    Ok(())
}

#[test]
fn test_agent_registry_from_config_with_agents() -> Result<()> {
    // Skip this test if GEMINI_API_KEY is not set
    if std::env::var("GEMINI_API_KEY").is_err() {
        eprintln!("Skipping test_agent_registry_from_config_with_agents: GEMINI_API_KEY not set");
        return Ok(());
    }

    let mut agent_configs = HashMap::new();

    agent_configs.insert(
        "enhancer".to_string(),
        AgentConfig {
            name: "enhancer".to_string(),
            role: "enhancer".to_string(),
            provider: "gemini".to_string(),
            model_name: "gemini-1.5-flash".to_string(),
            temperature: 0.7,
            top_p: 0.9,
            top_k: 40,
            max_output_tokens: 2048,
            max_retries: 3,
            retry_on_empty: true,
            require_json: true,
            extras: HashMap::new(),
        },
    );

    agent_configs.insert(
        "reviser".to_string(),
        AgentConfig {
            name: "reviser".to_string(),
            role: "reviser".to_string(),
            provider: "gemini".to_string(),
            model_name: "gemini-1.5-flash".to_string(),
            temperature: 0.8,
            top_p: 0.9,
            top_k: 40,
            max_output_tokens: 2048,
            max_retries: 3,
            retry_on_empty: true,
            require_json: true,
            extras: HashMap::new(),
        },
    );

    let registry = AgentRegistry::from_config(&agent_configs)?;
    let agents = registry.list();

    assert_eq!(agents.len(), 2);
    assert!(agents.contains(&"enhancer"));
    assert!(agents.contains(&"reviser"));

    // Verify we can get the agents
    let enhancer = registry.get("enhancer")?;
    assert_eq!(enhancer.config().role, "enhancer");

    let reviser = registry.get("reviser")?;
    assert_eq!(reviser.config().role, "reviser");

    Ok(())
}

#[test]
fn test_agent_registry_from_config_unsupported_provider() {
    let mut agent_configs = HashMap::new();

    agent_configs.insert(
        "test".to_string(),
        AgentConfig {
            name: "test".to_string(),
            role: "test".to_string(),
            provider: "unsupported_provider".to_string(),
            model_name: "test-model".to_string(),
            temperature: 0.7,
            top_p: 0.9,
            top_k: 40,
            max_output_tokens: 2048,
            max_retries: 3,
            retry_on_empty: true,
            require_json: false,
            extras: HashMap::new(),
        },
    );

    let result = AgentRegistry::from_config(&agent_configs);
    assert!(result.is_err());

    if let Err(e) = result {
        assert!(e.to_string().contains("not yet supported"));
    }
}

#[test]
fn test_agent_config_defaults() {
    let config = AgentConfig::default();

    assert_eq!(config.name, "default");
    assert_eq!(config.provider, "gemini");
    assert_eq!(config.role, "generic");
    assert_eq!(config.model_name, "gemini-1.5-flash");
    assert_eq!(config.temperature, 0.7);
    assert_eq!(config.top_p, 0.95);
    assert_eq!(config.top_k, 40);
    assert_eq!(config.max_output_tokens, 8192);
    assert_eq!(config.max_retries, 0);
    assert!(config.retry_on_empty);
    assert!(!config.require_json);
}

#[test]
fn test_agent_config_clone() {
    let config1 = AgentConfig {
        name: "test_agent".to_string(),
        role: "test_role".to_string(),
        provider: "gemini".to_string(),
        model_name: "gemini-1.5-flash".to_string(),
        temperature: 0.5,
        top_p: 0.8,
        top_k: 30,
        max_output_tokens: 1024,
        max_retries: 5,
        retry_on_empty: false,
        require_json: true,
        extras: HashMap::new(),
    };

    let config2 = config1.clone();

    assert_eq!(config1.name, config2.name);
    assert_eq!(config1.role, config2.role);
    assert_eq!(config1.provider, config2.provider);
    assert_eq!(config1.model_name, config2.model_name);
    assert_eq!(config1.temperature, config2.temperature);
    assert_eq!(config1.top_p, config2.top_p);
    assert_eq!(config1.top_k, config2.top_k);
    assert_eq!(config1.max_output_tokens, config2.max_output_tokens);
}

#[test]
fn test_agent_registry_list_sorted() -> Result<()> {
    // Skip if no API key
    if std::env::var("GEMINI_API_KEY").is_err() {
        eprintln!("Skipping test_agent_registry_list_sorted: GEMINI_API_KEY not set");
        return Ok(());
    }

    let mut agent_configs = HashMap::new();

    for name in &["charlie", "alice", "bob"] {
        agent_configs.insert(
            name.to_string(),
            AgentConfig {
                name: name.to_string(),
                role: format!("role_{}", name),
                provider: "gemini".to_string(),
                model_name: "gemini-1.5-flash".to_string(),
                ..Default::default()
            },
        );
    }

    let registry = AgentRegistry::from_config(&agent_configs)?;
    let agents = registry.list();

    assert_eq!(agents.len(), 3);
    // Note: HashMap doesn't guarantee order, but all should be present
    assert!(agents.contains(&"alice"));
    assert!(agents.contains(&"bob"));
    assert!(agents.contains(&"charlie"));

    Ok(())
}

#[test]
fn test_agent_defaults_new() {
    let defaults = AgentDefaults::new();
    assert_eq!(defaults.provider, "gemini");
    assert_eq!(defaults.model_name, "gemini-1.5-flash");
    assert_eq!(defaults.temperature, 0.7);
    assert_eq!(defaults.top_p, 0.95);
    assert_eq!(defaults.top_k, 40);
    assert_eq!(defaults.max_output_tokens, 8192);
    assert_eq!(defaults.max_retries, 3);
    assert!(defaults.retry_on_empty);
}

#[test]
fn test_agent_defaults_default() {
    let defaults = AgentDefaults::default();
    assert_eq!(defaults.provider, "gemini");
    assert_eq!(defaults.model_name, "gemini-1.5-flash");
}

#[test]
fn test_agent_defaults_apply_to() {
    let defaults = AgentDefaults::new();
    let mut config = AgentConfig {
        name: "test".to_string(),
        role: "test_role".to_string(),
        provider: String::new(),   // Empty - should be filled
        model_name: String::new(), // Empty - should be filled
        temperature: 0.0,          // Zero - should be filled
        top_p: 0.0,                // Zero - should be filled
        top_k: 0,                  // Zero - should be filled
        max_output_tokens: 0,      // Zero - should be filled
        max_retries: 0,            // Zero - should be filled
        retry_on_empty: false,
        require_json: true,
        extras: HashMap::new(),
    };

    defaults.apply_to(&mut config);

    assert_eq!(config.provider, "gemini");
    assert_eq!(config.model_name, "gemini-1.5-flash");
    assert_eq!(config.temperature, 0.7);
    assert_eq!(config.top_p, 0.95);
    assert_eq!(config.top_k, 40);
    assert_eq!(config.max_output_tokens, 8192);
    assert_eq!(config.max_retries, 3);
}

#[test]
fn test_agent_defaults_apply_to_preserves_existing() {
    let defaults = AgentDefaults::new();
    let mut config = AgentConfig {
        name: "test".to_string(),
        role: "test_role".to_string(),
        provider: "openai".to_string(),  // Should NOT be overwritten
        model_name: "gpt-4".to_string(), // Should NOT be overwritten
        temperature: 0.5,                // Non-zero - should NOT be overwritten
        top_p: 0.8,                      // Non-zero - should NOT be overwritten
        top_k: 20,                       // Non-zero - should NOT be overwritten
        max_output_tokens: 2048,         // Non-zero - should NOT be overwritten
        max_retries: 5,                  // Non-zero - should NOT be overwritten
        retry_on_empty: false,
        require_json: true,
        extras: HashMap::new(),
    };

    defaults.apply_to(&mut config);

    // Existing values should be preserved
    assert_eq!(config.provider, "openai");
    assert_eq!(config.model_name, "gpt-4");
    assert_eq!(config.temperature, 0.5);
    assert_eq!(config.top_p, 0.8);
    assert_eq!(config.top_k, 20);
    assert_eq!(config.max_output_tokens, 2048);
    assert_eq!(config.max_retries, 5);
}

#[test]
fn test_sync_agent_registry_new() {
    let registry = SyncAgentRegistry::new();
    assert_eq!(registry.list().len(), 0);
}

#[test]
fn test_sync_agent_registry_default() {
    let registry = SyncAgentRegistry::default();
    assert_eq!(registry.list().len(), 0);
}

#[test]
fn test_sync_agent_registry_contains() {
    let sync_registry = SyncAgentRegistry::new();

    // Should return false for non-existent agent
    assert!(!sync_registry.contains("nonexistent"));
}

#[test]
fn test_sync_agent_registry_clone() {
    let registry1 = SyncAgentRegistry::new();
    let registry2 = registry1.clone();

    // Both should be independent
    assert_eq!(registry1.list().len(), 0);
    assert_eq!(registry2.list().len(), 0);
}
