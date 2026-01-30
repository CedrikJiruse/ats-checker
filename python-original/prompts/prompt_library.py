"""
Modern AI Prompt Library with Best Practices

This module provides high-quality, provider-agnostic prompts using modern
prompt engineering techniques:
- Clear role definitions with expertise context
- Step-by-step instructions with reasoning
- Explicit output format specifications with examples
- Constraint enforcement (what NOT to do)
- Chain-of-thought reasoning for complex tasks
- XML/structured tags for content boundaries

Prompts support rendering for different providers:
- OpenAI: Uses system/user message format
- Anthropic: Uses system parameter + messages with prefill for JSON
- Generic: Single concatenated prompt (Gemini, Llama)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Base Prompt Template Class
# ============================================================================


class PromptTemplate(ABC):
    """
    Abstract base class for all prompt templates.
    Subclasses implement provider-specific rendering.
    """

    @abstractmethod
    def render(
        self, provider: str, **kwargs: Any
    ) -> str:
        """
        Render the prompt optimized for a specific provider.

        Args:
            provider: Provider name ('gemini', 'openai', 'anthropic', 'llama')
            **kwargs: Provider-specific parameters

        Returns:
            Formatted prompt string ready to send to the model
        """
        pass

    def to_openai_format(self, **kwargs: Any) -> List[Dict[str, str]]:
        """
        Convert to OpenAI message format: List[{"role": "system"/"user"/"assistant", "content": "..."}]

        Returns:
            List of message dictionaries for OpenAI API
        """
        raise NotImplementedError("Subclass must implement to_openai_format")

    def to_anthropic_format(
        self, **kwargs: Any
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Convert to Anthropic format: (system_prompt, messages)

        Returns:
            Tuple of (system_prompt_string, messages_list)
        """
        raise NotImplementedError("Subclass must implement to_anthropic_format")

    def to_generic_format(self, **kwargs: Any) -> str:
        """
        Convert to generic single-string format for Gemini/Llama.

        Returns:
            Complete prompt as a single string
        """
        raise NotImplementedError("Subclass must implement to_generic_format")


# ============================================================================
# Resume Enhancement Prompt
# ============================================================================


class ResumeEnhancementPrompt(PromptTemplate):
    """
    Modern resume enhancement prompt with best practices:
    - Expert role definition (ATS optimization expert)
    - Step-by-step process: Analyze → Enhance → Structure → Validate
    - Explicit JSON schema with field descriptions and examples
    - Constraint enforcement (never fabricate experience)
    - For job-tailored resumes: Reasoning explanation required
    """

    # Role and system context
    SYSTEM_ROLE = (
        "You are an elite ATS (Applicant Tracking System) optimization expert "
        "with 15+ years of experience in resume writing, HR technology, and career coaching. "
        "You excel at restructuring resumes to pass ATS systems while maintaining truthfulness "
        "and highlighting genuine accomplishments."
    )

    # Base enhancement instructions
    ENHANCEMENT_INSTRUCTIONS = """
You will process a resume and transform it into a high-quality, ATS-optimized structured format.

PROCESS (follow these steps in order):
1. ANALYZE: Examine the raw resume content. Identify structure, sections, and key information.
2. ENHANCE: Improve each section for clarity, impact, and ATS compatibility.
   - Use strong action verbs (led, implemented, delivered, optimized, etc.)
   - Quantify achievements where possible (increased by 25%, reduced costs by $50K, etc.)
   - Make implicit skills explicit (time management → "project timeline management")
   - Standardize date formats (all dates as MM/YYYY)
3. STRUCTURE: Organize the enhanced content into JSON according to the schema below.
4. VALIDATE: Verify each field is truthful, well-formatted, and ATS-compatible.

CRITICAL CONSTRAINTS (NON-NEGOTIABLE):
- NEVER fabricate employers, job titles, dates, degrees, or certifications.
- NEVER claim skills or experiences not mentioned in the original resume.
- NEVER invent company names, achievements, or credentials.
- You may only rephrase, restructure, and highlight existing content.
- Keep all dates and factual details exactly as provided.

OUTPUT FORMAT (JSON SCHEMA):
Return a valid JSON object with this exact structure:

{
  "personal_info": {
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1 (123) 456-7890",
    "location": "City, State",
    "linkedin": "https://linkedin.com/in/username or null",
    "github": "https://github.com/username or null",
    "portfolio": "https://portfolio.com or null"
  },
  "summary": "2-3 sentence professional summary highlighting expertise and key achievements",
  "experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "start_date": "MM/YYYY",
      "end_date": "MM/YYYY or 'Present'",
      "location": "City, State or Remote",
      "description": "2-3 sentence overview of role",
      "achievements": [
        "Action verb + specific achievement with metric or impact (e.g., 'Led team of 5 engineers...') - Present tense or past tense",
        "Quantifiable result where possible",
        "Keep each achievement to 1-2 sentences"
      ]
    }
  ],
  "education": [
    {
      "institution": "University Name",
      "degree": "Degree Type (e.g., Bachelor of Science)",
      "field": "Field of Study",
      "graduation_date": "MM/YYYY",
      "gpa": "3.8 (optional, include only if 3.5+)",
      "honors": ["Honors, scholarships, or awards (optional)"]
    }
  ],
  "skills": [
    "Skill 1 (relevant to industry)",
    "Skill 2",
    "Technical skills, programming languages, tools, frameworks, methodologies"
  ],
  "projects": [
    {
      "name": "Project Name",
      "description": "Brief description of project purpose",
      "technologies": ["Tech1", "Tech2", "Tech3"],
      "link": "https://github.com/... or null"
    }
  ]
}

OUTPUT REQUIREMENTS:
- Return ONLY the JSON object, no markdown formatting (no ```json), no commentary.
- Ensure the JSON is valid and parseable.
- All required fields must be present (even if empty/null).
- Arrays should contain at least one item (except optional fields).

RESUME CONTENT TO PROCESS:
"""

    # Job-tailoring instructions
    JOB_TAILORING_INSTRUCTIONS = """

JOB TAILORING (IMPORTANT):
You are tailoring this resume specifically to match the following job description.
Your goal is to highlight the most relevant experiences and skills.

TAILORING STRATEGY:
1. Identify 5-7 key requirements from the job description
2. Prioritize experiences that directly match these requirements
3. Reorder "achievements" to lead with job-relevant accomplishments
4. Adjust "summary" to reflect job-specific expertise
5. Emphasize skills mentioned in the job description
6. Add context: explain WHY these experiences make the candidate a good fit

REASONING (REQUIRED):
After generating the JSON, provide a brief explanation of your tailoring decisions:
- Which job requirements are most strongly matched?
- Which experiences did you prioritize and why?
- What keywords from the job description are now emphasized in the resume?

Job Description:
"""

    def render(
        self, provider: str, resume_content: str, job_description: Optional[str] = None
    ) -> str:
        """Render resume enhancement prompt for the specified provider."""
        if provider == "openai":
            messages = self.to_openai_format(
                resume_content=resume_content, job_description=job_description
            )
            # For OpenAI, combine messages into a single string for internal use
            # The actual OpenAI integration will handle the message format
            prompt = "\n\n".join(
                [f"[{m['role'].upper()}]\n{m['content']}" for m in messages]
            )
            return prompt
        elif provider == "anthropic":
            system, messages = self.to_anthropic_format(
                resume_content=resume_content, job_description=job_description
            )
            # Return formatted for Anthropic
            prompt = system + "\n\n"
            prompt += "\n\n".join(
                [f"[{m['role'].upper()}]\n{m['content']}" for m in messages]
            )
            return prompt
        else:
            # Generic format for Gemini, Llama, etc.
            return self.to_generic_format(
                resume_content=resume_content, job_description=job_description
            )

    def to_openai_format(
        self, resume_content: str, job_description: Optional[str] = None, **kwargs: Any
    ) -> List[Dict[str, str]]:
        """Convert to OpenAI message format."""
        system_content = self.SYSTEM_ROLE + "\n\n" + self.ENHANCEMENT_INSTRUCTIONS

        if job_description:
            system_content += "\n" + self.JOB_TAILORING_INSTRUCTIONS

        user_content = ""
        if job_description:
            user_content = (
                self.JOB_TAILORING_INSTRUCTIONS
                + job_description
                + "\n\nRESUME:\n"
                + resume_content
            )
        else:
            user_content = self.ENHANCEMENT_INSTRUCTIONS + resume_content

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def to_anthropic_format(
        self, resume_content: str, job_description: Optional[str] = None, **kwargs: Any
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Convert to Anthropic format with system parameter."""
        system = self.SYSTEM_ROLE + "\n\n" + self.ENHANCEMENT_INSTRUCTIONS

        if job_description:
            system += "\n" + self.JOB_TAILORING_INSTRUCTIONS

        user_content = ""
        if job_description:
            user_content = (
                "Job Description:\n"
                + job_description
                + "\n\nResume to enhance:\n"
                + resume_content
            )
        else:
            user_content = "Resume to enhance:\n" + resume_content

        # For JSON output, add prefill in the assistant's starting message
        messages = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": "{"},
        ]

        return system, messages

    def to_generic_format(
        self, resume_content: str, job_description: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Convert to generic single-string format."""
        prompt = self.SYSTEM_ROLE + "\n\n" + self.ENHANCEMENT_INSTRUCTIONS

        if job_description:
            prompt += "\n" + self.JOB_TAILORING_INSTRUCTIONS + job_description + "\n\n"

        prompt += resume_content
        prompt += (
            "\n\nOutput ONLY the JSON object, with no markdown formatting or commentary."
        )
        return prompt


# ============================================================================
# Job Summary Prompt
# ============================================================================


class JobSummaryPrompt(PromptTemplate):
    """
    Modern job summary prompt for extracting actionable job insights:
    - Technical recruiter persona
    - Structured 5-section output template
    - Keyword extraction with priority ranking
    - Must-have vs nice-to-have classification
    """

    SYSTEM_ROLE = (
        "You are an experienced technical recruiter specializing in resume-job matching "
        "and candidate positioning. Your expertise is identifying job requirements, "
        "extracting strategic keywords, and summarizing job descriptions for ATS optimization."
    )

    INSTRUCTIONS = """
Analyze the provided job description and extract actionable insights for resume optimization.

OUTPUT FORMAT (Plain text, follow this exact structure):

[ROLE SUMMARY]
One-sentence role summary highlighting the core position and primary focus.

[TOP RESPONSIBILITIES] (5 bullets)
- Most important daily/weekly responsibilities from the job description
- List in order of emphasis/importance
- Use the exact language from the job description where possible

[MUST-HAVE REQUIREMENTS] (5 bullets)
- Non-negotiable skills, experiences, or qualifications
- These are explicitly required or mentioned 3+ times in the job description
- Mark with importance level: [CRITICAL], [IMPORTANT], [REQUIRED]

[NICE-TO-HAVE] (3 bullets)
- Preferred but not required skills or experiences
- Bonus qualifications or "ideal candidate" traits

[ATS KEYWORDS] (comma-separated list)
Extract and rank keywords by importance for ATS systems:
1. Technical skills and technologies (programming languages, frameworks, tools)
2. Domain expertise (industry-specific knowledge)
3. Soft skills (leadership, communication, project management)
4. Certifications or degrees

EXTRACTION STRATEGY:
- Identify the top 5-7 job requirements by frequency and emphasis
- Mark MUST-HAVE for "required", "mandatory", or frequently mentioned skills
- Mark NICE-TO-HAVE for "preferred", "ideal", or rarely mentioned items
- Extract exact keywords and technical terms
- Preserve job title and industry terminology

EXAMPLE OUTPUT STRUCTURE (DO NOT MODIFY LABELS):
[ROLE SUMMARY]
Senior backend engineer building scalable cloud infrastructure for fintech platform.

[TOP RESPONSIBILITIES]
- Design and implement distributed microservices architecture
- Mentor junior engineers and conduct code reviews
- Lead performance optimization initiatives
- Collaborate with DevOps on infrastructure automation
- Own reliability and deployment strategy

[MUST-HAVE REQUIREMENTS]
- [CRITICAL] 5+ years backend software engineering experience
- [CRITICAL] Expert-level proficiency in Python or Java
- [REQUIRED] Experience with cloud platforms (AWS, GCP, or Azure)
- [IMPORTANT] Strong system design and database optimization skills
- [IMPORTANT] Experience with Kubernetes and containerization

[NICE-TO-HAVE]
- Experience with fintech or financial systems
- Mentoring or tech lead experience
- Open-source contributions

[ATS KEYWORDS]
Python, Java, AWS, Kubernetes, microservices, distributed systems, cloud architecture, system design, database optimization, CI/CD, Docker, leadership, mentoring
"""

    def render(
        self, provider: str, job_description: str, **kwargs: Any
    ) -> str:
        """Render job summary prompt for the specified provider."""
        if provider == "openai":
            messages = self.to_openai_format(job_description=job_description)
            prompt = "\n\n".join(
                [f"[{m['role'].upper()}]\n{m['content']}" for m in messages]
            )
            return prompt
        elif provider == "anthropic":
            system, messages = self.to_anthropic_format(job_description=job_description)
            prompt = system + "\n\n"
            prompt += "\n\n".join(
                [f"[{m['role'].upper()}]\n{m['content']}" for m in messages]
            )
            return prompt
        else:
            return self.to_generic_format(job_description=job_description)

    def to_openai_format(
        self, job_description: str, **kwargs: Any
    ) -> List[Dict[str, str]]:
        """Convert to OpenAI message format."""
        return [
            {"role": "system", "content": self.SYSTEM_ROLE},
            {"role": "user", "content": self.INSTRUCTIONS + "\n\nJob Description:\n" + job_description},
        ]

    def to_anthropic_format(
        self, job_description: str, **kwargs: Any
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Convert to Anthropic format."""
        return (
            self.SYSTEM_ROLE,
            [
                {
                    "role": "user",
                    "content": self.INSTRUCTIONS + "\n\nJob Description:\n" + job_description,
                }
            ],
        )

    def to_generic_format(self, job_description: str, **kwargs: Any) -> str:
        """Convert to generic single-string format."""
        return self.SYSTEM_ROLE + "\n\n" + self.INSTRUCTIONS + "\n\nJob Description:\n" + job_description


# ============================================================================
# Resume Revision Prompt
# ============================================================================


class RevisionPrompt(PromptTemplate):
    """
    Modern resume revision prompt for iterative improvement:
    - Iterative improvement context and awareness
    - Score-aware targeting (current score, target score, focus areas)
    - Specific improvement targets from score breakdown
    - Explanation of changes (diff-style reasoning)
    """

    SYSTEM_ROLE = (
        "You are an elite ATS resume optimization expert specializing in iterative improvement. "
        "You understand scoring systems and can strategically enhance resumes to improve specific metrics "
        "while maintaining truthfulness and professional standards."
    )

    BASE_INSTRUCTIONS = """
You will revise an already-structured resume JSON to improve its quality and ATS compatibility.

REVISION RULES (NON-NEGOTIABLE):
- NEVER fabricate employers, dates, degrees, or certifications
- You may only rephrase, enhance, and restructure existing content
- Maintain all factual accuracy - verify every claim is truthful
- Keep the same JSON schema as the input
- Preserve all dates, employers, and credentials exactly as provided
- Return ONLY the revised JSON object, no markdown formatting or commentary

REVISION STRATEGY:
1. Analyze the current resume structure and content
2. Identify improvement opportunities (wording, impact, clarity)
3. Focus on ATS optimization (keyword usage, metric visibility)
4. Apply changes strategically to address specific improvement areas
5. Verify all changes maintain truthfulness

JSON OUTPUT REQUIREMENTS:
- Return a complete, valid JSON object matching the input schema
- Preserve all fields and structure
- Ensure the output is parseable and valid
"""

    SCORE_AWARE_INSTRUCTIONS = """

SCORE-AWARE REVISION:
Previous Iteration Score: {current_score:.1f}/100
Target Score: {target_score:.1f}/100
Improvement Needed: {points_needed:.1f} points

FOCUS AREAS (prioritized by impact):
{focus_areas}

REVISION PRIORITIES:
1. Address the highest-impact focus areas first
2. Implement changes that directly address scoring weaknesses
3. Maintain authentic, truthful content
4. Explain your rationale for key changes

EXPLANATION REQUIRED:
After each significant revision, briefly explain:
- What was improved and why?
- How does this change impact the score?
- Is the change truthful and authentic?
"""

    JOB_TAILORING_INSTRUCTIONS = """

JOB TAILORING:
Tailor this revision specifically to match the provided job description.
Reorder achievements to highlight job-relevant accomplishments.
Emphasize keywords from the job description.

Job Description:
{job_description}
"""

    def render(
        self,
        provider: str,
        enhanced_resume_json: str,
        current_score: float = 0.0,
        target_score: float = 80.0,
        focus_areas: Optional[str] = None,
        job_description: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Render revision prompt for the specified provider."""
        if provider == "openai":
            messages = self.to_openai_format(
                enhanced_resume_json=enhanced_resume_json,
                current_score=current_score,
                target_score=target_score,
                focus_areas=focus_areas,
                job_description=job_description,
            )
            prompt = "\n\n".join(
                [f"[{m['role'].upper()}]\n{m['content']}" for m in messages]
            )
            return prompt
        elif provider == "anthropic":
            system, messages = self.to_anthropic_format(
                enhanced_resume_json=enhanced_resume_json,
                current_score=current_score,
                target_score=target_score,
                focus_areas=focus_areas,
                job_description=job_description,
            )
            prompt = system + "\n\n"
            prompt += "\n\n".join(
                [f"[{m['role'].upper()}]\n{m['content']}" for m in messages]
            )
            return prompt
        else:
            return self.to_generic_format(
                enhanced_resume_json=enhanced_resume_json,
                current_score=current_score,
                target_score=target_score,
                focus_areas=focus_areas,
                job_description=job_description,
            )

    def to_openai_format(
        self,
        enhanced_resume_json: str,
        current_score: float = 0.0,
        target_score: float = 80.0,
        focus_areas: Optional[str] = None,
        job_description: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, str]]:
        """Convert to OpenAI message format."""
        system_content = self.SYSTEM_ROLE + "\n\n" + self.BASE_INSTRUCTIONS

        points_needed = max(0, target_score - current_score)
        focus_text = (
            focus_areas or "No specific focus areas. Improve overall quality."
        )

        system_content += self.SCORE_AWARE_INSTRUCTIONS.format(
            current_score=current_score,
            target_score=target_score,
            points_needed=points_needed,
            focus_areas=focus_text,
        )

        if job_description:
            system_content += self.JOB_TAILORING_INSTRUCTIONS.format(
                job_description=job_description
            )

        user_content = "Resume JSON to revise:\n" + enhanced_resume_json

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def to_anthropic_format(
        self,
        enhanced_resume_json: str,
        current_score: float = 0.0,
        target_score: float = 80.0,
        focus_areas: Optional[str] = None,
        job_description: Optional[str] = None,
        **kwargs: Any,
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Convert to Anthropic format."""
        system = self.SYSTEM_ROLE + "\n\n" + self.BASE_INSTRUCTIONS

        points_needed = max(0, target_score - current_score)
        focus_text = (
            focus_areas or "No specific focus areas. Improve overall quality."
        )

        system += self.SCORE_AWARE_INSTRUCTIONS.format(
            current_score=current_score,
            target_score=target_score,
            points_needed=points_needed,
            focus_areas=focus_text,
        )

        if job_description:
            system += self.JOB_TAILORING_INSTRUCTIONS.format(
                job_description=job_description
            )

        user_content = "Resume JSON to revise:\n" + enhanced_resume_json

        # For JSON output, add prefill
        messages = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": "{"},
        ]

        return system, messages

    def to_generic_format(
        self,
        enhanced_resume_json: str,
        current_score: float = 0.0,
        target_score: float = 80.0,
        focus_areas: Optional[str] = None,
        job_description: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Convert to generic single-string format."""
        prompt = self.SYSTEM_ROLE + "\n\n" + self.BASE_INSTRUCTIONS

        points_needed = max(0, target_score - current_score)
        focus_text = (
            focus_areas or "No specific focus areas. Improve overall quality."
        )

        prompt += self.SCORE_AWARE_INSTRUCTIONS.format(
            current_score=current_score,
            target_score=target_score,
            points_needed=points_needed,
            focus_areas=focus_text,
        )

        if job_description:
            prompt += self.JOB_TAILORING_INSTRUCTIONS.format(
                job_description=job_description
            )

        prompt += "\n\nResume JSON to revise:\n" + enhanced_resume_json
        prompt += "\n\nOutput ONLY the revised JSON object with no markdown formatting or commentary."
        return prompt
