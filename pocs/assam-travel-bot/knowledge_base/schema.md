# Knowledge Base Schema

Derived from `/mnt/d/Projects/oxomiai/oxomi-core/documentation/docs/surveys.md`.

Each place entry follows the survey field schema and maps to the travel bot's KB retrieval layer (vector search + metadata filtering).

## Data structure (JSON)

```json
{
  "site_id": "kamakhya_guwahati",
  "site_name": "Kamakhya Temple",
  "site_type": "temple",
  "district": "Guwahati",
  "region": "Guwahati",
  
  "address": "Kamakhya, Nilachal Hill, Guwahati, Assam 781010",
  "latitude": 26.166426,
  "longitude": 91.705509,
  
  "short_description": "Major Shakti Peetha and Tantric center...",
  "historical_significance": "One of 51 ancient Shakti Peethas...",
  "unique_attractions": ["Tantric tradition", "Ambubachi Mela", "Mahavidyas complex"],
  
  "visiting_hours": "5:30 AM – 1:00 PM, 2:30 PM – 7:30 PM",
  "average_time_spent_hours": 3,
  "aarti_timings": {
    "morning": "5:30 AM",
    "main_doors": "8:00 AM",
    "evening": "5:15 PM",
    "sandhya": "7:30 PM"
  },
  
  "entry_fee_details": "General darshan free; Special darshan ₹50",
  "entry_required": false,
  "best_seasons": ["Winter", "Spring"],
  "avoid_seasons": ["Monsoon"],
  
  "food_options": "Licensed vendors, local prasad",
  "parking": { "on_site": true, "capacity": "Medium" },
  
  "nearby_hotels": ["Hotel Shreemoyee Inn", "Radisson Blu"],
  "nearby_restaurants": ["Mast Punjabi Dhaba", "Mandala Multi-cuisine"],
  
  "targeted_festivals": ["Ambubachi Mela (June)"],
  "contact_phone": "+91-XXXX-XXXX",
  "contact_email": "info@example.com",
  "official_website": "https://example.com",
  
  "verification_status": "verified",
  "last_verified_date": "2024-08-15",
  
  "embedding_text": "Major Shakti Peetha and Tantric center dedicated to Goddess Kamakhya..."
}
```

## Storage

- **Format**: JSON lines or CSV (one place per line/row)
- **Location**: `knowledge_base/places.jsonl` (one JSON object per line)
- **Indexing**: Vector embeddings on `embedding_text` (concat of name, description, attractions, significance) for semantic search; metadata filters (district, site_type, season) for structured queries.

## Migration from oxomi-core surveys

The schema above maps directly from `surveys.md`:
- `site_name`, `site_type`, `address`, `latitude`/`longitude` → direct from survey
- `short_description` → from "Short description" section
- `visiting_hours`, `average_time_spent_hours`, `aarti_timings` → from survey sections
- `entry_fee_details`, `entry_required` → from "Entry, Tickets & Visitor Logistics"
- `unique_attractions` → from survey's "Unique Attractions" list
- `best_seasons`, `avoid_seasons` → inferred or from recommendations
- `embedding_text` → concatenation of key fields for semantic search

To onboard a real place, verify against the survey checklist and fill all fields, then add one JSON line to `places.jsonl`.
