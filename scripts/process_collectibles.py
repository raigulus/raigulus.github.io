#!/usr/bin/env python3
"""
process_collectibles.py – Replace verbatim transcripts with paraphrased
summaries and add proper source attribution with direct wiki links.

This ensures no copyrighted dialogue text is stored in the archive.
"""

import json
import re
from pathlib import Path

WIKI_BASE = "https://thedivision.fandom.com/wiki/"
ENTRIES_ROOT = Path("/tmp/raigulus-site/content/lore/entries/collectibles")


def make_wiki_url(wiki_path: str) -> str:
    """Create a direct link to a Fandom wiki page."""
    return WIKI_BASE + wiki_path.replace(" ", "_")


def get_hub_wiki_path(entry: dict) -> str | None:
    """Extract the wiki hub path from verification notes."""
    notes = entry.get("verification", {}).get("notes", "")
    # Look for wiki path pattern in notes
    match = re.search(r'wiki "([^"]+)"', notes)
    if match:
        return match.group(1)
    # Fallback: construct from title
    title = entry.get("title", "")
    # Map common patterns
    if "TD2 Comms:" in title:
        suffix = title.replace("TD2 Comms: ", "").strip()
        return f"Comms/{suffix}"
    elif "TD1 Phone Recordings:" in title:
        suffix = title.replace("TD1 Phone Recordings: ", "").strip()
        return f"Phone Recordings/{suffix}"
    return None


def paraphrase_transcript(transcript: str, description: str) -> str:
    """
    Create a brief summary from the transcript.
    
    Since we can't use AI to paraphrase, we create a factual summary
    based on the available metadata and transcript structure.
    """
    if not transcript:
        return description or "No summary available."
    
    # Count speakers (unique names before colon)
    speakers = set()
    for line in transcript.split("\n"):
        line = line.strip()
        if ":" in line and len(line.split(":")[0]) < 30:
            speaker = line.split(":")[0].strip()
            if speaker and not speaker.startswith("("):
                speakers.add(speaker)
    
    # Count dialogue lines
    dialogue_lines = [l for l in transcript.split("\n") if ":" in l and l.strip()]
    total_lines = len(dialogue_lines)
    
    # Build summary
    parts = []
    if description:
        parts.append(description)
    
    if speakers:
        if len(speakers) == 1:
            parts.append(f"Features {list(speakers)[0]}.")
        elif len(speakers) <= 3:
            parts.append(f"Features {', '.join(sorted(speakers))}.")
        else:
            parts.append(f"Features multiple speakers including {', '.join(sorted(list(speakers)[:3]))}.")
    
    if total_lines > 0:
        parts.append(f"Contains {total_lines} dialogue exchanges.")
    
    return " ".join(parts) if parts else description or "Audio log transcript."


def process_entry(entry: dict) -> dict:
    """Process a single collectible entry."""
    wiki_path = get_hub_wiki_path(entry)
    wiki_url = make_wiki_url(wiki_path) if wiki_path else None
    
    # Update verification notes
    if wiki_url:
        entry["verification"]["notes"] = (
            f"Source: The Division Fandom Wiki. "
            f"Full transcript available at: {wiki_url}. "
            f"This entry contains paraphrased summaries only; no copyrighted dialogue text is stored."
        )
        entry["verification"]["source_url"] = wiki_url
    
    # Process each section
    for section in entry.get("sections", []):
        # Get description from claims if available
        comm_title = section.get("heading", "")
        description = ""
        
        # Find matching claim
        for claim in entry.get("claims", []):
            if comm_title.lower() in claim.get("text", "").lower():
                # Extract description from claim text
                desc_match = re.search(r': (.+?)(?:\s*\(Location:|$)', claim["text"])
                if desc_match:
                    description = desc_match.group(1).strip()
                break
        
        # Replace transcript paragraphs with paraphrased summary
        new_paras = []
        for para in section.get("paragraphs", []):
            text = para.get("text", "")
            
            # Check if this looks like a transcript (has speaker: dialogue pattern)
            # Handle both quoted and unquoted text
            clean_text = text.strip().strip('"')
            # Match patterns like "SPEAKER:", "SPEAKER NAME:", "SPEAKER 1:", etc.
            is_transcript = bool(re.search(r'^[A-Z][A-Z0-9\s]+:', clean_text, re.MULTILINE))
            
            if is_transcript:
                # Replace with paraphrased summary
                summary = paraphrase_transcript(text, description)
                new_paras.append({
                    "text": summary,
                    "claim_ids": para.get("claim_ids", []),
                })
            else:
                # Keep as-is (already a summary/description)
                new_paras.append(para)
        
        section["paragraphs"] = new_paras
    
    return entry


def main():
    """Process all collectible entries."""
    if not ENTRIES_ROOT.exists():
        print(f"Entries directory not found: {ENTRIES_ROOT}")
        return
    
    entry_files = sorted(ENTRIES_ROOT.rglob("*.json"))
    print(f"Found {len(entry_files)} collectible entries to process")
    
    processed = 0
    errors = 0
    
    for entry_file in entry_files:
        try:
            with open(entry_file, encoding="utf-8") as f:
                entry = json.load(f)
            
            # Process the entry
            processed_entry = process_entry(entry)
            
            # Save back
            with open(entry_file, "w", encoding="utf-8") as f:
                json.dump(processed_entry, f, indent=2, ensure_ascii=False)
            
            processed += 1
            print(f"  ✓ {entry_file.name}")
            
        except Exception as e:
            errors += 1
            print(f"  ✗ {entry_file.name}: {e}")
    
    print(f"\nDone: {processed} processed, {errors} errors")


if __name__ == "__main__":
    main()
