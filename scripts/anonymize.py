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
STRIP_SUFFIXES = [" Villalobos", " Millón", " Prieto", "Aranguren", " Baque", " Goffard"]


def anonymize_name(name: str) -> str:
    """Replace real name with anonymized version, stripping leftover surnames."""
    for real, fake in ANONYM_MAP.items():
        if name.startswith(real):
            result = fake
            remainder = name[len(real):]
            # Strip known surname fragments
            for suffix in STRIP_SUFFIXES:
                remainder = remainder.replace(suffix, "")
            # Keep only _ID suffix if present
            if remainder:
                result = f"{fake}{remainder}"
            return result
    # Handle already-partially-anonymized names
    for prefix in ["Alumna", "Alumno"]:
        if name.startswith(prefix):
            result = name
            for suffix in STRIP_SUFFIXES:
                result = result.replace(suffix, "")
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
