"""Shared identity fixtures for the business card and vCard tests."""

_SECRET = "secret:some.vault.key"

FIXTURES = {
    "full": {
        "name": "Ari Vale",
        "email": {"agentmail": {"address": "ari@agentmail.to", "api_key": _SECRET}},
        "phone": {"agentphone": {"number": "+14155550100", "number_id": "n1", "agent_id": "a1", "api_key": _SECRET}},
        "whatsapp": {"status": "active", "number": "+14155550100"},
        "wallet": {"evm": {"address": "0xABC"}},
        "accounts": {"github": {"username": "ari-vale", "vault": _SECRET}},
        "face": {"photo": None, "seed": "Ari Vale"},
        "social": {
            "twitter":  {"handle": "arivale",  "token": _SECRET},
            "linkedin": {"handle": "ari-vale", "token": _SECRET},
        },
        "calendar": {"local": None, "booking_url": "https://cal.com/ari-vale/15min"},
        "address": {"line1": "123 Main St", "city": "San Francisco"},
        "domain": {"name": "arivale.ai"},
        "entity": {"name": None},
        "business_card": {
            "title":   "AI Agent",
            "tagline": "Built to get things done.",
            "website": "https://arivale.ai",
        },
    },
    "minimal": {
        "name": "Mira Chen",
        "email": {"agentmail": {"address": "mira@agentmail.to", "api_key": _SECRET}},
    },
    "stress": {
        "name": "Archibald Jonathan Worthington Pemberton-Smythe",
        "business_card": {
            "title":   "Chief Executive Officer and Grand Vizier of Automated Decisions",
            "tagline": "I help forward-thinking organisations harness the untapped "
                       "potential of AI-driven automation to achieve outcomes at scale.",
            "website": "https://very-long-domain-name-for-testing-purposes.example.com",
        },
        "email": {"agentmail": {"address": "a.j.worthington-pemberton-smythe@agentmail.to"}},
        "phone": {"agentphone": {"number": "+442071234567"}},
        "social": {
            "twitter":   {"handle": "ajwpembertonsmythe", "token": _SECRET},
            "linkedin":  {"handle": "archibald-worthington", "token": _SECRET},
            "instagram": {"handle": "archie_pembs", "token": _SECRET},
        },
        "address": {"line1": "Suite 1000, 1 Canada Square, Canary Wharf", "city": "London"},
        "calendar": {"booking_url": "https://cal.com/archibald-worthington/30min"},
        "face": {"seed": "Archibald Worthington"},
    },
    "arabic": {
        "name": "نور حديد",  # Noor Hadid
        "business_card": {
            "title":   "وكيل ذكاء اصطناعي",
            "tagline": "خدمات الذكاء الاصطناعي",
            "website": "https://noor-hadid.ai",
        },
        "email": {"agentmail": {"address": "noor@agentmail.to"}},
        "phone": {"agentphone": {"number": "+971501234567"}},
        "face": {"seed": "Noor Hadid"},
    },
    "nophone": {
        "name": "Kit Okafor",
        "email": {"agentmail": {"address": "kit@agentmail.to"}},
        "business_card": {"title": None, "tagline": None, "website": "agenthub.dev"},
        "face": {"seed": "Kit Okafor"},
    },
    "injection": {
        "name": "Evil\r\nBEGIN:VCARD\r\n",
        "business_card": {
            "title":   "END:VCARD;A;B;C",
            "tagline":  "A" * 600,
            "website": "https://safe.example.com",
        },
        "email": {"agentmail": {"address": "test@example.com"}},
        "face": {"seed": "injection"},
    },
}
