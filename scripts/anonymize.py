"""Anonymize student names in the database for GDPR compliance."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import Database
from src.config import get_config

ANONYM_MAP = {
    "Ana Cristina Barrios Alconada": "Alumna A",
    "Ander Pena": "Alumno B",
    "Ander Pena Villalobos": "Alumno B",
    "Angelos Ampatzidis": "Alumno C",
    "Fernando Benjamin Sánchez Llorens": "Alumno D",
    "Fernando Sánchez": "Alumno D",
    "Florencia Giordano Dode": "Alumna E",
    "Francisco Fletcher Sanfeliú": "Alumno F",
    "Francisco Olivenza": "Alumno G",
    "Francisco Olivenza Millón": "Alumno G",
    "Ibai Cosgaya": "Alumno H",
    "Ibai Cosgaya Prieto": "Alumno H",
    "Iñigo López Ayala": "Alumno I",
    "Jamal ATIF ARIF": "Alumno J",
    "Jamal Atif Arif": "Alumno J",
    "Jon Itsazain Martin Bilbao": "Alumno K",
    "Lenny Tatiana Quispe Gonzales": "Alumna L",
    "Miguel Pozo": "Alumno M",
    "Miguel Pozo Aranguren": "Alumno M",
    "Mikel Guillén": "Alumno N",
    "Mikel Guillén Baque": "Alumno N",
    "Nagore Juarez": "Alumna Ñ",
    "Naiara Sarachaga": "Alumna O",
    "Naiara Sarachaga Goffard": "Alumna O",
    "Nerea López Ziluaga": "Alumna P",
    "Zigor Apraiz Garteiz": "Alumno Q",
}

# Suffixes to strip (leftover surname fragments)
STRIP_SUFFIXES = [" Villalobos", " Millón", " Prieto", " Aranguren", " Baque", " Goffard"]


def anonymize_name(name: str) -> str:
    """Replace real name with anonymized version, stripping leftover surnames."""
    # Handle already-anonymized names (strip leftover surnames)
    for prefix in ["Alumna", "Alumno"]:
        if name.startswith(prefix):
            result = name
            for suffix in STRIP_SUFFIXES:
                result = result.replace(suffix, "")
            result = result.replace("  ", " ").strip()
            return result

    # Try exact match first, then partial (handle "Name ID" format)
    for real, fake in ANONYM_MAP.items():
        if name == real or name.startswith(real + "_") or name.startswith(real + " "):
            result = fake
            remainder = name[len(real):]
            for suffix in STRIP_SUFFIXES:
                remainder = remainder.replace(suffix, "")
            # Clean up: remove leading space, collapse doubles
            remainder = remainder.lstrip("_").lstrip()
            if remainder and not remainder.startswith("_"):
                remainder = "_" + remainder
            result = f"{fake}{remainder}"
            return result

    # Fallback: check if name contains any known real name as substring
    for real, fake in ANONYM_MAP.items():
        if real in name:
            result = fake
            remainder = name.replace(real, "")
            for suffix in STRIP_SUFFIXES:
                remainder = remainder.replace(suffix, "")
            remainder = remainder.strip("_").strip()
            if remainder:
                result = f"{fake}_{remainder}"
            return result

    return name


def main():
    config = get_config()
    db = Database(config.database.path)

    students = db.get_all_students()
    print(f"Found {len(students)} student records\n")

    for student in students:
        old_name = student["name"]
        new_name = anonymize_name(old_name)
        if old_name != new_name:
            db.conn.execute(
                "UPDATE students SET name = ? WHERE id = ?",
                (new_name, student["id"]),
            )
            print(f"  {old_name} → {new_name}")

    db.conn.commit()
    print(f"\nDatabase anonymized. New names:")
    for s in db.get_all_students():
        print(f"  {s['name']}")

    db.close()


if __name__ == "__main__":
    main()
