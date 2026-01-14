"""
Tests for prompt library with provider-specific rendering.

Tests the modern prompt templates and their provider-specific formatting.
"""

import json
import pytest

from prompts.prompt_library import (
    ResumeEnhancementPrompt,
    JobSummaryPrompt,
    RevisionPrompt,
)


class TestResumeEnhancementPrompt:
    """Test ResumeEnhancementPrompt rendering across providers."""

    @pytest.fixture
    def prompt_template(self):
        return ResumeEnhancementPrompt()

    @pytest.fixture
    def sample_resume(self):
        return """
        John Doe
        john@example.com
        (555) 123-4567

        EXPERIENCE:
        Software Engineer at TechCorp (2020-2023)
        - Built web applications
        - Fixed bugs
        - Worked with Python
        """

    @pytest.fixture
    def sample_job(self):
        return """
        Senior Python Developer
        Requirements:
        - 5+ years Python experience
        - REST API design
        - Docker and Kubernetes
        - AWS cloud platform
        """

    def test_generic_format_includes_resume_content(self, prompt_template, sample_resume):
        """Test that generic format includes the resume content."""
        prompt = prompt_template.to_generic_format(resume_content=sample_resume)
        assert sample_resume in prompt
        assert "ATS" in prompt and "optimization expert" in prompt.lower()

    def test_generic_format_with_job_description(
        self, prompt_template, sample_resume, sample_job
    ):
        """Test that generic format includes job description when provided."""
        prompt = prompt_template.to_generic_format(
            resume_content=sample_resume, job_description=sample_job
        )
        assert sample_resume in prompt
        assert sample_job in prompt
        assert "tailor" in prompt.lower()

    def test_openai_format_returns_message_list(
        self, prompt_template, sample_resume
    ):
        """Test that OpenAI format returns list of messages."""
        messages = prompt_template.to_openai_format(resume_content=sample_resume)
        assert isinstance(messages, list)
        assert len(messages) >= 2
        assert all(isinstance(m, dict) for m in messages)
        assert all("role" in m and "content" in m for m in messages)

    def test_openai_format_has_system_and_user(
        self, prompt_template, sample_resume
    ):
        """Test that OpenAI format includes system and user roles."""
        messages = prompt_template.to_openai_format(resume_content=sample_resume)
        roles = [m["role"] for m in messages]
        assert "system" in roles or "user" in roles

    def test_anthropic_format_returns_tuple(self, prompt_template, sample_resume):
        """Test that Anthropic format returns (system, messages) tuple."""
        system, messages = prompt_template.to_anthropic_format(
            resume_content=sample_resume
        )
        assert isinstance(system, str)
        assert isinstance(messages, list)
        assert len(system) > 0
        assert len(messages) > 0

    def test_anthropic_format_includes_prefill(self, prompt_template, sample_resume):
        """Test that Anthropic format includes assistant prefill for JSON."""
        system, messages = prompt_template.to_anthropic_format(
            resume_content=sample_resume
        )
        # Should have user and assistant messages for prefill
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    def test_render_generic_provider(self, prompt_template, sample_resume):
        """Test render method with generic provider."""
        prompt = prompt_template.render(
            provider="gemini", resume_content=sample_resume
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "ATS" in prompt or "expert" in prompt.lower()

    def test_render_with_job_tailoring(self, prompt_template, sample_resume, sample_job):
        """Test render method with job tailoring."""
        prompt = prompt_template.render(
            provider="gemini",
            resume_content=sample_resume,
            job_description=sample_job,
        )
        assert sample_job in prompt
        assert "tailor" in prompt.lower()

    def test_generic_format_contains_json_schema(
        self, prompt_template, sample_resume
    ):
        """Test that generic format explains JSON schema."""
        prompt = prompt_template.to_generic_format(resume_content=sample_resume)
        assert "personal_info" in prompt
        assert "experience" in prompt
        assert "education" in prompt
        assert "skills" in prompt

    def test_generic_format_includes_constraints(
        self, prompt_template, sample_resume
    ):
        """Test that prompt includes constraint enforcement."""
        prompt = prompt_template.to_generic_format(resume_content=sample_resume)
        assert "never" in prompt.lower() or "fabricate" in prompt.lower()


class TestJobSummaryPrompt:
    """Test JobSummaryPrompt rendering across providers."""

    @pytest.fixture
    def prompt_template(self):
        return JobSummaryPrompt()

    @pytest.fixture
    def sample_job_description(self):
        return """
        Senior Python Developer

        We're looking for an experienced Python developer to lead our backend team.

        Responsibilities:
        - Design and implement microservices
        - Lead code review process
        - Mentor junior developers
        - Optimize database queries
        - Deploy to production

        Requirements:
        - 5+ years Python development
        - Experience with Django or Flask
        - AWS or GCP experience
        - Strong SQL skills
        - Bachelor's degree in CS or related field

        Nice to have:
        - Open source contributions
        - Kubernetes experience
        - Published technical articles
        """

    def test_generic_format_includes_job_description(
        self, prompt_template, sample_job_description
    ):
        """Test that generic format includes job description."""
        prompt = prompt_template.to_generic_format(
            job_description=sample_job_description
        )
        assert sample_job_description in prompt

    def test_generic_format_mentions_recruiter_role(
        self, prompt_template, sample_job_description
    ):
        """Test that prompt includes recruiter persona."""
        prompt = prompt_template.to_generic_format(
            job_description=sample_job_description
        )
        assert "recruiter" in prompt.lower()

    def test_openai_format_structure(self, prompt_template, sample_job_description):
        """Test OpenAI format structure."""
        messages = prompt_template.to_openai_format(
            job_description=sample_job_description
        )
        assert isinstance(messages, list)
        assert len(messages) >= 2
        assert all(isinstance(m, dict) for m in messages)

    def test_anthropic_format_structure(self, prompt_template, sample_job_description):
        """Test Anthropic format structure."""
        system, messages = prompt_template.to_anthropic_format(
            job_description=sample_job_description
        )
        assert isinstance(system, str)
        assert isinstance(messages, list)

    def test_render_returns_string(self, prompt_template, sample_job_description):
        """Test that render method returns a string."""
        prompt = prompt_template.render(
            provider="gemini", job_description=sample_job_description
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_includes_output_format_sections(
        self, prompt_template, sample_job_description
    ):
        """Test that prompt specifies output format sections."""
        prompt = prompt_template.to_generic_format(
            job_description=sample_job_description
        )
        assert "[ROLE SUMMARY]" in prompt or "role" in prompt.lower()
        assert "[TOP RESPONSIBILITIES]" in prompt or "responsibilities" in prompt.lower()
        assert "[MUST-HAVE" in prompt or "must-have" in prompt.lower()
        assert "[NICE-TO-HAVE" in prompt or "nice-to-have" in prompt.lower()
        assert "[ATS KEYWORDS]" in prompt or "keywords" in prompt.lower()


class TestRevisionPrompt:
    """Test RevisionPrompt rendering across providers."""

    @pytest.fixture
    def prompt_template(self):
        return RevisionPrompt()

    @pytest.fixture
    def sample_resume_json(self):
        return json.dumps({
            "personal_info": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1 (555) 123-4567",
            },
            "summary": "Software engineer with 5 years experience",
            "experience": [
                {
                    "company": "TechCorp",
                    "title": "Software Engineer",
                    "start_date": "01/2020",
                    "end_date": "Present",
                    "achievements": ["Built web apps", "Fixed bugs"],
                }
            ],
            "skills": ["Python", "JavaScript"],
        })

    def test_generic_format_includes_resume_json(
        self, prompt_template, sample_resume_json
    ):
        """Test that generic format includes resume JSON."""
        prompt = prompt_template.to_generic_format(
            enhanced_resume_json=sample_resume_json
        )
        assert sample_resume_json in prompt

    def test_generic_format_with_scores(
        self, prompt_template, sample_resume_json
    ):
        """Test that generic format includes score information."""
        prompt = prompt_template.to_generic_format(
            enhanced_resume_json=sample_resume_json,
            current_score=72.5,
            target_score=85.0,
        )
        assert "72.5" in prompt or "current" in prompt.lower()
        assert "85.0" in prompt or "target" in prompt.lower()

    def test_generic_format_with_focus_areas(
        self, prompt_template, sample_resume_json
    ):
        """Test that generic format includes focus areas."""
        focus_areas = "- Improve keyword alignment\n- Add metrics to achievements"
        prompt = prompt_template.to_generic_format(
            enhanced_resume_json=sample_resume_json,
            focus_areas=focus_areas,
        )
        assert "keyword" in prompt.lower()
        assert "metrics" in prompt.lower()

    def test_openai_format_structure(self, prompt_template, sample_resume_json):
        """Test OpenAI format structure."""
        messages = prompt_template.to_openai_format(
            enhanced_resume_json=sample_resume_json
        )
        assert isinstance(messages, list)
        assert len(messages) >= 2

    def test_anthropic_format_structure(self, prompt_template, sample_resume_json):
        """Test Anthropic format structure."""
        system, messages = prompt_template.to_anthropic_format(
            enhanced_resume_json=sample_resume_json
        )
        assert isinstance(system, str)
        assert isinstance(messages, list)

    def test_render_with_job_description(
        self, prompt_template, sample_resume_json
    ):
        """Test render with job description for tailoring."""
        job_desc = "Senior Python Developer at tech company"
        prompt = prompt_template.render(
            provider="gemini",
            enhanced_resume_json=sample_resume_json,
            job_description=job_desc,
        )
        assert job_desc in prompt

    def test_prompt_includes_revision_rules(
        self, prompt_template, sample_resume_json
    ):
        """Test that prompt includes revision rules."""
        prompt = prompt_template.to_generic_format(
            enhanced_resume_json=sample_resume_json
        )
        assert "fabricate" in prompt.lower() or "never" in prompt.lower()
        assert "truthful" in prompt.lower() or "authentic" in prompt.lower()

    def test_score_aware_improvement_targeting(
        self, prompt_template, sample_resume_json
    ):
        """Test that score-aware revision includes targeted improvements."""
        prompt = prompt_template.to_generic_format(
            enhanced_resume_json=sample_resume_json,
            current_score=65.0,
            target_score=80.0,
            focus_areas="- Improve ATS keyword match (5 points)\n- Add metrics (3 points)",
        )
        assert "15.0" in prompt or "improvement" in prompt.lower()


class TestPromptProviderCompatibility:
    """Test that all prompts work with all providers."""

    @pytest.mark.parametrize("provider", ["gemini", "openai", "anthropic", "llama"])
    def test_resume_enhancement_all_providers(self, provider):
        """Test ResumeEnhancementPrompt with all providers."""
        prompt = ResumeEnhancementPrompt()
        result = prompt.render(
            provider=provider,
            resume_content="Test resume content",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("provider", ["gemini", "openai", "anthropic", "llama"])
    def test_job_summary_all_providers(self, provider):
        """Test JobSummaryPrompt with all providers."""
        prompt = JobSummaryPrompt()
        result = prompt.render(
            provider=provider,
            job_description="Test job description",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("provider", ["gemini", "openai", "anthropic", "llama"])
    def test_revision_all_providers(self, provider):
        """Test RevisionPrompt with all providers."""
        prompt = RevisionPrompt()
        result = prompt.render(
            provider=provider,
            enhanced_resume_json='{"test": "data"}',
        )
        assert isinstance(result, str)
        assert len(result) > 0
