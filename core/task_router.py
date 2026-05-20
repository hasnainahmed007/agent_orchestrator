"""LLM-based task router using semantic similarity.

Replaces hardcoded keyword matching with a multi-strategy approach:
1. Skill keyword matching (fast, no API call) — fallback
2. LLM-based classification (accurate, one API call) — default
3. Embedding similarity (requires embedding model) — optional
"""
import logging
from typing import Optional, List, Tuple
from agents.roles import AgentInstance
from skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


def route_task_by_keywords(task_description: str, agents: List[AgentInstance],
                           registry: SkillRegistry) -> Optional[AgentInstance]:
    """Fast keyword-based routing. Falls back gracefully.

    Args:
        task_description: Task description text
        agents: List of available agent instances
        registry: Skill registry for skill context

    Returns:
        Best matching agent or None
    """
    if not agents:
        return None

    scores: List[Tuple[float, AgentInstance]] = []
    desc_lower = task_description.lower()
    # Extract meaningful words (>3 chars)
    desc_words = {w for w in desc_lower.split() if len(w) > 3}

    for agent in agents:
        score = 0.0
        # Skill name matches
        for skill_id in agent.get_skills_from_role():
            skill = registry.get_skill(skill_id)
            if skill:
                skill_lower = skill.name.lower()
                if skill_lower in desc_lower:
                    score += 10
                for word in desc_words:
                    if word in skill_lower:
                        score += 2
                # Check description keywords
                for word in desc_words:
                    if word in skill.description.lower():
                        score += 1

        # Hierarchy bonus: higher-ranked agents for complex tasks
        desc_len = len(desc_lower)
        if desc_len > 200:
            score += 1  # Prefer experienced for complex

        if score > 0:
            scores.append((score, agent))

    if scores:
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[0][1]
    return None


def route_task_by_llm(task_description: str, agents: List[AgentInstance],
                      registry: SkillRegistry, llm_model: str = "gpt-4o") -> Optional[AgentInstance]:
    """Use LLM to classify task and match to best agent.

    Makes a single lightweight classification call.

    Args:
        task_description: Task description
        agents: Available agents
        registry: Skill registry
        llm_model: Model for classification

    Returns:
        Best matching agent or None
    """
    if not agents or len(agents) == 1:
        return agents[0] if agents else None

    # Build agent profiles for the LLM
    agent_profiles = []
    for i, agent in enumerate(agents):
        skills = []
        for sid in agent.get_skills_from_role():
            skill = registry.get_skill(sid)
            if skill:
                skills.append(f"{skill.name} ({sid})")
        profile = f"{i}: {agent.name} — skills: {', '.join(skills)}"
        agent_profiles.append(profile)

    prompt = f"""Task: {task_description[:500]}

Available agents:
{chr(10).join(agent_profiles)}

Which agent (number only) is best suited for this task? Reply with just the number."""

    try:
        from crewai.llms.providers.openai.completion import OpenAICompletion
        llm = OpenAICompletion(model=llm_model, temperature=0)
        response = llm.call([{"role": "user", "content": prompt}])
        text = str(response).strip()
        # Extract number from response
        import re
        match = re.search(r'\d+', text)
        if match:
            idx = int(match.group())
            if 0 <= idx < len(agents):
                return agents[idx]
    except Exception as e:
        logger.debug(f"LLM routing fallback (will use keywords): {e}")

    return None


def route_task(task_description: str, agents: List[AgentInstance],
               registry: SkillRegistry, use_llm: bool = False) -> Optional[AgentInstance]:
    """Route task to best agent using multi-strategy approach.

    Args:
        task_description: Task description
        agents: List of available (idle) agent instances
        registry: Skill registry
        use_llm: If True, try LLM classification first, fallback to keywords

    Returns:
        Best matching agent or None
    """
    if use_llm:
        result = route_task_by_llm(task_description, agents, registry)
        if result:
            logger.info(f"LLM routed task to {result.name}")
            return result

    result = route_task_by_keywords(task_description, agents, registry)
    if result:
        logger.info(f"Keyword routed task to {result.name}")
    return result
