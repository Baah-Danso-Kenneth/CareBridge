from backend.app.utils import logging
import json
import logging
from typing import Dict, Any, List

from app.agents.base import A2AAgent, A2AAgentCard, A2ATask, A2ATaskStatus
from app.prompts.medical_prompts import CRITIC_SYSTEM_PROMPT, CRITIC_HUMAN_PROMPT

logger = logging.getLogger(__name__)



class CriticAgent(A2AAgent):
    """
    Critic Agent - Evaluates recommendations and decides if they need revision

    Scores on:
    - Safety (40 points)
    - Clarity (30 points)
    - completeness (30 points)


    Verdicts:
    - PASS: Score >= 70, proceed to output
    - REVISE: Score < 70, loop back to executor
    """


    def _register_card(self) ->A2AAgentCard:
        return A2AAgentCard(
            name="critic-agent",
            version="1.0.0",
            description="Evaluates healthcare recommendations and triggers correctins",
            capabilities=["recommendation_scoring", "safety_evaluation", "self_correction"],
            input_modes=["recommendation"],
            output_modes = ["score", "verdict"],
            endpoint="in-process://critic-agent",
            skills=[{
                "name": "evaluate_recommendation",
                "description": "Score and evaluate recommendation quality",
                "input": {"recommendation": "string", "symptoms": "string"},
                "output": {"score": "float", "verdict": "string", "feedback": "string"}
            }]
        )


    def process_task(self, task: A2ATask) -> A2ATask:
        """Evaluate recommendation and issue verdict """
        task.update_status(A2ATaskStatus.WORKING)
        logger.info(f"CriticAgent: evaluating recommendation")

        try:
            recommendation = task.context.get("recommendation", "")
            symptoms = task.context.get("symptoms", "")
            attempt = task.context.get("attempt",1)

            if not recommendation:
                task.errors.append("No recommendation provided")
                task.update_status(A2ATaskStatus.FAILED)
                return task

            evaluation = self._score_recommendation(recommendation, symptoms)
            total_score = evaluation["total_score"]
            issues = evaluation.get("issues",[])

            verdict = self._determine_verdict(total_score, issues, attempt)

            task.result = {
                "score": total_score,
                "verdict": verdict,
                "feedback": evaluation["feedback"],
                "scores": evaluation["scores"],
                "issues": issues,
                "attempt": attempt
            }

            task.update_status(A2ATaskStatus.COMPLETED)
            logger.info(f"CriticAgent: verdict={verdict}, Score={total_score}/100")

        
        except Exception as e:
            logger.error(f"CriticAgent failed: {e}")
            task.errors.append(str(e))
            task.update_status(A2ATaskStatus.FAILED)

        self._record_task(task)
        return task



    def _score_recommendation(self, recommendation: str, symptoms: str) -> Dict[str, Any]:
        """Score recommendation across multiple dimensions"""

        recommendation_lower = recommendation.lower()
        issues = []
        scores = {}

        safety_score = 40
        dangerous_patterns = [
            "guarantee", "definitely", "certain",
            "always", "never", "stop taking", "ignore your doctor",
        ]

        for pattern in dangerous_patterns:
            if pattern in recommendation_lower:
                safety_score -= 10
                issues.append({"dimension": "safety", "pattern": pattern, "severity": "HIGH"})

        scores["safety"] = max(0, safety_score)   

        clarity_score = 30
        if len(recommendation) < 50:
            clarity_score -= 10
            issues.append({"dimension": "clarity", "message": "Too Short", "severity": "MEDIUM"})  

        elif len(recommendation) > 500:
            clarity_score -= 5
            issues.append({"dimension": "clarity", "message": "Too Long", "severity": "LOW"})

        action_indicators = ["should", "need to", "suggest", "call", "see", "go", "to"]

        has_actions = any(indicator in recommendation for indicator in action_indicators)
        if not has_actions:
            clarity_score -= 10
            issues.append({"dimension": "clarity", "message": "Missing actionable steps", "seveity": "MEDIUM"})

        disclaimer_indicators = ["not medical advice", "consult a", "healthcare proffessional", "see a doctor"]
        has_disclaimer = any(indicator in recommendation_lower for indicator in disclaimer_indicators)

        if not has_disclaimer:
            clarity_score -= 10
            issues.append({"dimension": "Clarity", "message": "Missing disclaimer", "severity": "HIGH"})

        scores["clarity"] = max(0, clarity_score)

        completeness_score = 30

        urgency_keywords = ["emergency", "urgent", "soon", "routine","asap"]
        if not any(keyword in recommendation_lower for keyword in urgency_keywords):
            completeness_score -= 10
            issues.append({"dimension": "completeness", "message": "Missing urgency level", "severity": "MEDIUM"})

        
        symptom_words = symptoms.lower().split()[:5]
        if not any(word in recommendation_lower for word in symptom_words):
            completeness_score -= 5
        
        scores["completeness"] = max(0, completeness_score)

        total_score = sum(scores.values())

        feedback = self._generate_feedback(scores, total_score, issues)

        return {
            "scores": scores,
            "total_score": total_score,
            "feedback": feedback,
            "issues": issues
        }


    def _determine_verdict(self, score: int, issues: List[Dict], attempt: int) -> str:
        """Determine verdict based on score and attempt count"""
        max_attempt = 3

        critical_issues = [i for i in issues if i.get("severity") == "HIGH"]
        if critical_issues and score < 60:
            return "REVISE"

        if score >= 70:
            return "PASS"

        elif attempt >= max_attempt:
            logger.info(f"Max attempts ({max_attempt}), reached forcing PASS")
            return "PASS"
               
        else:
            return "REVISE"

    

    def _generate_feedback(self, scores: Dict[str, int], total: int, issues: List[Dict]):
        """Generate human-reliable feedback for executor"""
        feedback_parts = []

        if scores["safety"] < 35:
            feedback_parts.append("Safety concerns detected. Removedefinitive lanuate like 'guarantee' or 'definitely'.")

        if scores["clarity"] < 20:
            feedback_parts.append("Improve clarity. Add disclaimer and actionable steps")
        
        if scores["completeness"] < 20:
            feedback_parts.append("Add urgency level and address patient's specific symptoms.")

        if not feedback_parts:
            feedback_parts.append(f"Good quality. Score: {total}/100")

        return " ".join(feedback_parts)


    def _llm_evaluate(self, recommendation: str, symptoms: str) -> Dict[str, Any]:
        """Optional LLM-based evaluation for complex cases"""
        try:
            human_prompt = CRITIC_HUMAN_PROMPT.format(
                recommendation=recommendation,
                symptoms=symptoms
            )

            response = self._invoke_llm(CRITIC_SYSTEM_PROMPT, CRITIC_HUMAN_PROMPT)

            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()

            return json.load(clean)
        
        except Exception as e:
            logger.warning(f"LLM evaluation failed: {e}")
            return {"score": 50, "verdict": "REVISE", "feeback": "EValuation Failed"}














