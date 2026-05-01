import json
from pathlib import Path



def create_default_knowledge(output_path: str = "data/medical_knowledge.json"):
    """Create a default medical knowledge base for testing"""


    knowledge = {
        "documents": [
            {
            "text": "Chest pain can indicate heart attack. Seek emergency care immediately",
            "metadata": {"source": "Clinical guidelines", "category": "emergency"}
            },
            {
                "text": "Headache with fever may indicate viral infection. Rest and hydrate.",
                "metadata": {"source": "Clinical guidelines", "category": "common"}
            },
            {
                "text": "Shortness of breath requires immediate medical attention. ",
                "metadata": {"source": "Clinical guidelines", "category": "emergency"}
            }
        ]
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(knowledge, f, indent=2)

    return output_path
