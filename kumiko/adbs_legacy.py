from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
QUESTION_DIR = CONTENT_DIR / "questions"
QUESTION_TRANSLATIONS_FILE = CONTENT_DIR / "questions.en.json"
STATUS_VALUES = {"active", "archived", "deleted"}
BASE_GLOSSARY_QUESTION_COUNT = 69
SLIDES = [
    {
        "id": "nosql",
        "title": "Introduction to NoSQL Systems",
        "file": "ADBS-NoSQL.pdf",
        "path": "/lecture_slides/ADBS-NoSQL.pdf",
    },
    {
        "id": "key-value",
        "title": "Key-Value Stores",
        "file": "ADBS-KeyValueStores.pdf",
        "path": "/lecture_slides/ADBS-KeyValueStores.pdf",
    },
    {
        "id": "document",
        "title": "Document Stores",
        "file": "ADBS-DocumentStores.pdf",
        "path": "/lecture_slides/ADBS-DocumentStores.pdf",
    },
    {
        "id": "graph",
        "title": "Graph Databases",
        "file": "ADBS-Graph.pdf",
        "path": "/lecture_slides/ADBS-Graph.pdf",
    },
    {
        "id": "column",
        "title": "Column-Oriented Databases",
        "file": "ADBS-ColumnStores.pdf",
        "path": "/lecture_slides/ADBS-ColumnStores.pdf",
    },
]

SECTION_TERM_OVERRIDES = {
    ("nosql", 0): [
        "Schemaless",
        "Schema-on-Read",
        "Application Database",
        "Integration Database",
        "Aggregate",
    ],
    ("nosql", 1): [
        "Bitcask",
        "Document Store",
        "Property Graph",
        "Column Store",
        "Wide Column Store",
    ],
    ("nosql", 2): [
        "Aggregate",
        "Sharding",
        "Reference",
        "Embedding",
        "Property Graph",
    ],
    ("nosql", 7): [
        "Happened-Before",
        "Lamport Clock",
        "Vector Clock",
        "Version Stamp",
        "Causal Consistency",
    ],
    ("key-value", 0): [
        "Point Query",
        "Range Query",
        "Put Operation",
        "Get Operation",
        "Log-Structured Storage",
    ],
    ("document", 6): [
        "JSON",
        "Document Store",
        "Document Validation",
        "JSON Schema",
        "Shard Key",
    ],
    ("graph", 2): [
        "ACID",
        "Bookmark",
        "Sharding",
        "Replication",
        "Read-Your-Writes",
    ],
    ("graph", 5): [
        "MERGE",
        "DETACH DELETE",
        "Property",
        "Uniqueness Constraint",
        "Existence Constraint",
    ],
    ("column", 6): [
        "Timestamp",
        "Column Family",
        "Row Key",
        "Tablet",
        "Wide Column Store",
    ],
    ("column", 7): [
        "Chubby",
        "SSTable",
        "Wide Column Store",
        "Column Family",
        "Tablet",
    ],
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_optional_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return read_json(path)


def multilingual(de: str, en: str) -> dict[str, str]:
    return {"de": de, "en": en}


def localized_pair(value: Any, english: Any, field: str) -> dict[str, str]:
    german = value.get("de") if isinstance(value, dict) else value
    english_value = english.get("en") if isinstance(english, dict) else english
    if not isinstance(german, str) or not german.strip():
        raise ValueError(f"{field}: deutscher Text fehlt")
    if not isinstance(english_value, str) or not english_value.strip():
        raise ValueError(f"{field}: englischer Text fehlt")
    return multilingual(german, english_value)


def apply_question_translation(
    question: dict[str, Any], translation: dict[str, Any] | None
) -> dict[str, Any]:
    question_id = question.get("id", "<unknown>")
    if not isinstance(translation, dict):
        raise ValueError(f"{question_id}: englische Übersetzung fehlt")

    localized = dict(question)
    for field in ("prompt", "explanation"):
        localized[field] = localized_pair(
            question.get(field),
            translation.get(field),
            f"{question_id}.{field}",
        )
    if "context" in question:
        localized["context"] = localized_pair(
            question["context"],
            translation.get("context"),
            f"{question_id}.context",
        )

    translated_options = translation.get("options")
    if not isinstance(translated_options, dict):
        raise ValueError(f"{question_id}.options: englische Übersetzungen fehlen")
    localized_options = []
    for option in question.get("options", []):
        option_id = option.get("id", "<unknown>")
        translated_option = translated_options.get(option_id)
        if not isinstance(translated_option, dict):
            raise ValueError(
                f"{question_id}.options.{option_id}: englische Übersetzung fehlt"
            )
        localized_option = dict(option)
        for field in ("text", "explanation"):
            localized_option[field] = localized_pair(
                option.get(field),
                translated_option.get(field),
                f"{question_id}.options.{option_id}.{field}",
            )
        localized_options.append(localized_option)

    localized["options"] = localized_options
    localized["languages"] = ["de", "en"]
    return localized


def has_language(value: Any, language: str) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get(language), str)
        and bool(value[language].strip())
    )


def validate_question_languages(question: dict[str, Any]) -> None:
    question_id = question["id"]
    for language in ("de", "en"):
        for field in ("prompt", "explanation"):
            if not has_language(question.get(field), language):
                raise ValueError(f"{question_id}.{field}: Text für {language} fehlt")
        if "context" in question and not has_language(
            question["context"], language
        ):
            raise ValueError(f"{question_id}.context: Text für {language} fehlt")
        for option in question["options"]:
            for field in ("text", "explanation"):
                if not has_language(option.get(field), language):
                    raise ValueError(
                        f"{question_id}.options.{option['id']}.{field}: "
                        f"Text für {language} fehlt"
                    )


def validate_question(question: dict[str, Any], topic_ids: set[str]) -> None:
    question_id = question.get("id")
    options = question.get("options")
    if not question_id or not isinstance(options, list) or len(options) < 2:
        raise ValueError("jede Frage benötigt id und mindestens zwei Optionen")
    if question.get("topic") not in topic_ids:
        raise ValueError(f"{question_id}: unbekanntes topic '{question.get('topic')}'")
    if question.get("difficulty") not in range(1, 6):
        raise ValueError(f"{question_id}: difficulty muss zwischen 1 und 5 liegen")
    if question.get("status", "active") not in STATUS_VALUES:
        raise ValueError(
            f"{question_id}: status muss active, archived oder deleted sein"
        )
    if not all(
        isinstance(option.get("correct"), bool)
        and option.get("id")
        and option.get("text")
        for option in options
    ):
        raise ValueError(
            f"{question_id}: Optionen benötigen id, text und boolesches correct"
        )
    option_ids = [option["id"] for option in options]
    if len(option_ids) != len(set(option_ids)):
        raise ValueError(f"{question_id}: doppelte Option-ID")
    validate_question_languages(question)


def localize_glossary(glossary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    english = {
        entry["term"]: entry
        for entry in (
            read_optional_json(CONTENT_DIR / "glossary.en.json", [])
            + read_optional_json(CONTENT_DIR / "glossary.extra.en.json", [])
        )
    }
    localized = []
    for entry in glossary:
        item = dict(entry)
        if entry["term"] in english:
            item.setdefault("translations", {})["en"] = english[entry["term"]]
        localized.append(item)
    return localized


def default_tags(entry: dict[str, Any]) -> list[str]:
    topic_tags = {
        "nosql": ["NoSQL", "Distributed Systems"],
        "key-value": ["Key-Value", "Storage Engine"],
        "document": ["Document Store", "MongoDB"],
        "graph": ["Graph", "Cypher"],
        "column": ["Column Store", "Analytics"],
    }
    tags = set(topic_tags.get(entry["topic"], []))
    tags.update(entry.get("tags", []))
    tags.update(entry.get("aliases", []))
    term = entry["term"]
    if "Clock" in term:
        tags.add("Logical Clocks")
    if "Concern" in term or "Preference" in term:
        tags.add("MongoDB Guarantees")
    if "Encoding" in term or term in {"Compression", "Bitmap Index"}:
        tags.add("Compression")
    if term in {"CAP-Theorem", "PACELC", "Availability", "Partition Tolerance"}:
        tags.add("CAP")
    return sorted(tags)


SEARCH_STOPWORDS = {
    "aber",
    "als",
    "auch",
    "auf",
    "aus",
    "bei",
    "das",
    "der",
    "die",
    "ein",
    "eine",
    "einer",
    "eines",
    "für",
    "ist",
    "mit",
    "nach",
    "oder",
    "pro",
    "sich",
    "sind",
    "und",
    "von",
    "wird",
    "werden",
    "the",
    "and",
    "for",
    "from",
    "into",
    "that",
    "this",
    "with",
    "system",
    "systems",
    "store",
    "stores",
}

CONCRETE_EXAMPLES = {
    "Replication": multilingual(
        "Ein Produktdatensatz liegt auf drei Knoten. Fällt ein Knoten aus, kann ein anderes Replikat Reads bedienen; bei asynchroner Replikation kann dieses Replikat kurzzeitig noch den alten Preis enthalten.",
        "A product record is stored on three nodes. If one node fails, another replica can serve reads, although asynchronous replication may briefly expose the old price.",
    ),
    "AP-System": multilingual(
        "Während einer Netzwerkpartition akzeptieren beide erreichbaren Clusterhälften weiterhin Warenkorb-Updates. Nach Wiederherstellung der Verbindung müssen widersprüchliche Versionen zusammengeführt werden.",
        "During a network partition, both reachable cluster halves continue accepting shopping-cart updates. Conflicting versions must be reconciled after communication is restored.",
    ),
    "Causal Consistency": multilingual(
        "Ein Nutzer veröffentlicht Beitrag P und danach Antwort A auf P. Jeder Beobachter, der A sieht, muss zuvor oder gleichzeitig auch P sehen; unabhängige Beiträge dürfen unterschiedlich geordnet sein.",
        "A user publishes post P and then reply A to P. Every observer who sees A must also see P, while unrelated posts may be ordered differently.",
    ),
    "CP-System": multilingual(
        "Bei einer Partition verweigert die Minderheitsseite einen Write, weil sie den aktuellen Mehrheitsstand nicht sicher kennt. Die Antwort bleibt konsistent, aber diese Seite ist für den Write nicht verfügbar.",
        "During a partition, the minority side rejects a write because it cannot safely know the current majority state. Consistency is preserved, but that side is unavailable for the write.",
    ),
    "Manifest": multilingual(
        "Eine Compaction erzeugt SSTable 23 und ersetzt SSTables 11 und 14. Das Manifest protokolliert „23 hinzufügen, 11 und 14 entfernen“, damit der Store nach einem Neustart seinen gültigen Dateisatz kennt.",
        "A compaction creates SSTable 23 and replaces SSTables 11 and 14. The manifest records adding 23 and removing 11 and 14 so recovery can reconstruct the valid file set.",
    ),
    "Inconsistency Window": multilingual(
        "Der Primary bestätigt einen neuen Profilnamen um 10:00:00; ein Secondary übernimmt ihn erst um 10:00:02. Diese zwei Sekunden bilden für diesen Write das Inconsistency Window.",
        "The primary confirms a new profile name at 10:00:00 and a secondary applies it at 10:00:02. Those two seconds form the inconsistency window for that write.",
    ),
    "Write Amplification": multilingual(
        "Eine Anwendung schreibt logisch 1 MB. WAL, Flush und spätere Compactions schreiben zusammen 9 MB auf das Speichermedium; die Write Amplification beträgt damit 9.",
        "An application logically writes 1 MB. WAL, flush, and later compactions write 9 MB to storage in total, giving a write amplification of 9.",
    ),
    "Shard Key": multilingual(
        "Bei einer Orders-Collection verteilt ein gehashter customerId-Shard-Key Kunden gleichmäßiger. Ein monoton wachsender timestamp als alleiniger Shard Key kann neue Writes auf einen Hot Shard konzentrieren.",
        "For an orders collection, a hashed customerId shard key distributes customers more evenly. A monotonically increasing timestamp alone can concentrate new writes on one hot shard.",
    ),
    "Index-Free Adjacency": multilingual(
        "Vom Person-Knoten Alice gelangt Neo4j über direkt gespeicherte Nachbarschaftsverweise zu ihren FRIEND-Beziehungen, ohne zuerst eine globale Fremdschlüssel-Tabelle zu joinen.",
        "From the Alice person node, Neo4j follows directly stored adjacency references to FRIEND relationships without first joining a global foreign-key table.",
    ),
    "Node Key": multilingual(
        "Für Airport-Knoten kann die Kombination aus code und country als Node Key dienen: Beide Properties müssen vorhanden sein und ihre Kombination muss eindeutig bleiben.",
        "For Airport nodes, code plus country can form a node key: both properties must exist and their combination must remain unique.",
    ),
    "Virtual ID": multilingual(
        "Der 17. Wert in jeder unkomprimierten Spaltendatei gehört zur logischen Zeile 17. Die Position 17 dient als ID, ohne dass neben jedem Wert eine zusätzliche Tuple-ID gespeichert wird.",
        "The 17th value in each uncompressed column file belongs to logical row 17. Position 17 acts as the ID without storing an extra tuple ID beside every value.",
    ),
    "Wide Column Store": multilingual(
        "Ein Messwert wird unter Row Key sensor-42, Column data:temperature und Timestamp 10:05 gespeichert. Ein weiterer Qualifier data:humidity kann nur für Rows existieren, die ihn tatsächlich benötigen.",
        "A measurement is stored under row key sensor-42, column data:temperature, and timestamp 10:05. Another qualifier data:humidity may exist only for rows that need it.",
    ),
    "Schemaless": multilingual(
        "In derselben Collection enthält Dokument A nur name und email, Dokument B zusätzlich phone und Dokument C ein verschachteltes address-Objekt. Die Datenbank erzwingt beim Schreiben kein identisches starres Feldschema.",
        "In one collection, document A has name and email, document B also has phone, and document C has a nested address object. The database does not enforce one identical rigid write schema.",
    ),
    "Schema-on-Read": multilingual(
        "Alte Logeinträge besitzen clientIp, neue Einträge zusätzlich deviceType. Die Auswertung entscheidet beim Lesen, wie fehlende deviceType-Werte behandelt und beide Versionen gemeinsam interpretiert werden.",
        "Old log records contain clientIp while newer records also contain deviceType. The reader decides how to interpret missing deviceType values across both versions.",
    ),
    "Application Database": multilingual(
        "Ein Empfehlungssystem erhält einen eigenen Graph Store, während der Checkout einen Document Store nutzt. Jedes System wird für die Zugriffsmuster genau einer Anwendung gewählt.",
        "A recommendation service gets its own graph store while checkout uses a document store. Each database is selected for one application's access patterns.",
    ),
    "Integration Database": multilingual(
        "ERP, Reporting und Lagerverwaltung greifen auf dieselbe zentrale Kundendatenbank zu. Das gemeinsame Schema und systemübergreifende Integrität sind wichtiger als eine Optimierung für nur eine Anwendung.",
        "ERP, reporting, and warehouse systems share one central customer database. A shared schema and cross-system integrity matter more than optimizing for one application.",
    ),
    "Network Partition": multilingual(
        "Die Knoten A und B können miteinander kommunizieren, C und D ebenfalls, aber zwischen beiden Gruppen gehen alle Nachrichten verloren. Beide Gruppen laufen weiter, kennen jedoch die Updates der jeweils anderen Seite nicht.",
        "Nodes A and B can communicate, as can C and D, but all messages between the groups are lost. Both groups continue running without seeing the other side's updates.",
    ),
    "Optimistic Conflict Resolution": multilingual(
        "Zwei offline arbeitende Clients ändern denselben Kontakt. Der Store nimmt beide Versionen an; nach der Synchronisation entscheidet eine Merge-Regel oder der Benutzer, welche Felder übernommen werden.",
        "Two offline clients edit the same contact. The store accepts both versions; after synchronization, a merge rule or the user resolves the fields.",
    ),
    "Pessimistic Conflict Prevention": multilingual(
        "Bevor ein Client einen Lagerbestand ändert, sperrt er den Datensatz. Ein zweiter Client muss warten und kann dadurch keinen parallelen widersprüchlichen Write erzeugen.",
        "Before changing inventory, a client locks the record. A second client must wait and cannot create a conflicting concurrent write.",
    ),
    "Writes Follow Reads": multilingual(
        "Eine Session liest Preisversion v5 und schreibt daraufhin einen Rabatt. Wer den Rabatt-Write sieht, muss mindestens auch die zugrunde liegende Preisversion v5 sehen.",
        "A session reads price version v5 and then writes a discount based on it. Anyone observing the discount must also observe at least price version v5.",
    ),
    "Log-Structured Storage": multilingual(
        "Ein Update von k=A auf k=B überschreibt A nicht an seiner alten Position. Stattdessen wird der neue Eintrag k=B am Dateiende angehängt und der Index auf ihn umgebogen.",
        "Updating k=A to k=B does not overwrite A in place. A new k=B record is appended at the file end and the index is redirected to it.",
    ),
    "Active Data File": multilingual(
        "Bitcask hängt einen neuen put(k,v)-Eintrag ausschließlich an die aktuell aktive Datei an. Erreicht sie ihre Größen Grenze, wird sie geschlossen und eine neue aktive Datei begonnen.",
        "Bitcask appends a new put(k,v) record only to the active file. Once it reaches its size limit, it is closed and a new active file is started.",
    ),
    "Immutable Data File": multilingual(
        "Nach dem Schließen wird eine Bitcask-Datei nicht mehr verändert. Gets dürfen weiter auf ihre Einträge zeigen; ein Merge ersetzt sie später durch neu erzeugte bereinigte Dateien.",
        "After a Bitcask file is closed, it is never modified. Gets may still reference its entries until merge replaces it with newly written compacted files.",
    ),
    "Put Operation": multilingual(
        "put(user:7, v2) hängt v2 an die aktive Datei an und ändert den Keydir-Eintrag für user:7 auf neuen Offset und neue Größe; die ältere Version bleibt zunächst physisch liegen.",
        "put(user:7, v2) appends v2 to the active file and redirects the keydir entry for user:7 to the new offset and size; the old version remains physically present.",
    ),
    "Get Operation": multilingual(
        "get(user:7) schlägt user:7 in der Keydir nach und liest den Value mit genau einem gezielten Zugriff aus der dort angegebenen Datei und Position.",
        "get(user:7) looks up user:7 in keydir and reads the value with one targeted access to the recorded file and offset.",
    ),
    "Merge Process": multilingual(
        "Die Dateien enthalten k=A, später k=B und anschließend einen Tombstone für x. Der Merge kopiert nur die aktuell lebende Version k=B in neue Dateien und lässt veraltete Versionen sowie sicher entfernbaren Tombstone-Müll zurück.",
        "Files contain k=A, later k=B, and then a tombstone for x. Merge copies only the current live version k=B into new files and drops obsolete versions plus safely removable tombstone data.",
    ),
    "Delete Operation": multilingual(
        "delete(user:7) schreibt einen Tombstone in das Log. Ein späteres Get behandelt den Key als gelöscht, obwohl ältere Value-Einträge physisch bis zum Merge oder zur Compaction existieren.",
        "delete(user:7) appends a tombstone. A later get treats the key as deleted even though older value records remain physically present until merge or compaction.",
    ),
    "Level-0": multilingual(
        "Zwei nacheinander geflushte SSTables auf Level 0 enthalten beide Keys aus dem Bereich a–m. Ein Get für h muss deshalb potenziell beide Dateien prüfen.",
        "Two SSTables flushed to level 0 both contain keys in the range a–m. A get for h may therefore need to check both files.",
    ),
    "Sparse Index": multilingual(
        "Ein SSTable-Index speichert nur die Startkeys apple, mango und zebra seiner Datenblöcke. Für orange wird der Block ab mango gewählt und anschließend innerhalb dieses Blocks gesucht.",
        "An SSTable index stores only the block start keys apple, mango, and zebra. A lookup for orange selects the block beginning at mango and searches within it.",
    ),
    "BSON Document Limit": multilingual(
        "Ein Produktdokument wächst durch eingebettete Messwerte über 16 MB. Es kann so nicht gespeichert werden; die Messwerte müssen beispielsweise in eine separate Collection ausgelagert werden.",
        "A product document grows beyond 16 MB because of embedded measurements. It cannot be stored that way, so the measurements need a separate collection or another model.",
    ),
    "JSON Schema": multilingual(
        "Eine Collection verlangt per JSON Schema, dass email ein String und age eine nichtnegative Zahl ist. Ein Dokument mit age: 'alt' wird von der Validierung abgelehnt.",
        "A collection uses JSON Schema to require email to be a string and age a non-negative number. A document with age: 'old' is rejected.",
    ),
    "Array of References": multilingual(
        "Ein Autor-Dokument speichert bookIds: [b17,b42,b91]. Die Bücher bleiben eigene Dokumente und werden bei Bedarf über diese IDs nachgeladen.",
        "An author document stores bookIds: [b17,b42,b91]. The books remain separate documents and are loaded through those IDs when needed.",
    ),
    "Document Validation": multilingual(
        "Eine MongoDB-Collection akzeptiert neue Booking-Dokumente nur, wenn checkIn ein Datum und roomId ein String ist. Ein fehlerhaftes Dokument wird bereits beim Write zurückgewiesen.",
        "A MongoDB collection accepts new booking documents only when checkIn is a date and roomId is a string. An invalid document is rejected on write.",
    ),
    "Relationship Type": multilingual(
        "(:Person)-[:WORKS_AT]->(:Company) und (:Person)-[:LIVES_IN]->(:City) verbinden Knoten, tragen aber unterschiedliche fachliche Bedeutungen durch ihre Relationship Types.",
        "(:Person)-[:WORKS_AT]->(:Company) and (:Person)-[:LIVES_IN]->(:City) connect nodes but express different semantics through their relationship types.",
    ),
    "Variable-Length Path": multilingual(
        "MATCH (a)-[:FLIGHT*1..2]->(b) findet direkte Flüge und Verbindungen mit genau einem Umstieg, weil ein oder zwei FLIGHT-Beziehungen erlaubt sind.",
        "MATCH (a)-[:FLIGHT*1..2]->(b) finds direct flights and routes with exactly one stop because one or two FLIGHT relationships are allowed.",
    ),
    "Zero-Length Path": multilingual(
        "Das Pattern (a)-[:R*0..1]->(b) darf a selbst als b liefern: Bei Pfadlänge 0 wird keine Beziehung durchlaufen und der Pfad besteht nur aus dem Startknoten.",
        "The pattern (a)-[:R*0..1]->(b) may return a itself as b: at length zero no relationship is traversed and the path contains only the start node.",
    ),
    "Existence Constraint": multilingual(
        "Ein Constraint verlangt, dass jeder Airport-Knoten die Property code besitzt. CREATE (:Airport {name:'Vienna'}) wird deshalb ohne code abgewiesen.",
        "A constraint requires every Airport node to have a code property. CREATE (:Airport {name:'Vienna'}) is rejected without code.",
    ),
    "Vertical Fragmentation": multilingual(
        "Die Relation Sales(id,date,region,amount) wird in getrennte Spaltenfragmente für id, date, region und amount zerlegt; gemeinsame Positions- oder Tuple-IDs erlauben die Rekonstruktion.",
        "Sales(id,date,region,amount) is split into separate column fragments for id, date, region, and amount; shared positions or tuple IDs permit reconstruction.",
    ),
    "Explicit ID": multilingual(
        "Die amount-Spalte speichert (101,49.90), (102,12.00). Die erste Komponente ist die explizite Tuple-ID und verbindet die Werte mit den anderen Spalten derselben logischen Zeile.",
        "The amount column stores (101,49.90), (102,12.00). The first component is the explicit tuple ID linking values to the other columns of the same logical row.",
    ),
    "Position List": multilingual(
        "Ein Filter amount > 100 liefert [2,5,9]. Erst für diese drei Positionen werden anschließend customerId und date aus ihren Spalten nachgeladen.",
        "A filter amount > 100 returns [2,5,9]. Only those positions are then used to fetch customerId and date from their columns.",
    ),
    "Bitmap Index": multilingual(
        "Für die Spalte status mit den Werten open, paid und cancelled existiert je Wert ein Bitvektor. Eine Query status='paid' liest direkt die gesetzten Positionen im paid-Bitvektor.",
        "For a status column with values open, paid, and cancelled, one bit vector exists per value. A status='paid' query reads the set positions in the paid vector.",
    ),
    "Column Qualifier": multilingual(
        "In der Family contact verwendet eine Row contact:email und contact:phone, eine andere nur contact:email. email und phone sind dynamische Qualifier innerhalb derselben Family.",
        "Within family contact, one row uses contact:email and contact:phone while another uses only contact:email. Email and phone are dynamic qualifiers in the same family.",
    ),
}

CONCEPT_PITFALLS = {
    "Causal Consistency": multilingual(
        "Kausale Konsistenz erzwingt keine einzige globale Reihenfolge für unabhängige Ereignisse. Sie ordnet nur Ereignisse, zwischen denen eine kausale Abhängigkeit besteht.",
        "Causal consistency does not impose one global order on independent events. It orders only events connected by a causal dependency.",
    ),
    "Replication": multilingual(
        "Replikation ist nicht Sharding: Replikate speichern Kopien derselben Daten. Außerdem kann ein erreichbares Secondary trotz Verfügbarkeit einen veralteten Stand liefern.",
        "Replication is not sharding: replicas store copies of the same data. A reachable secondary may still return stale data.",
    ),
    "Shard Key": multilingual(
        "Ein vorhandener Shard Key garantiert noch keine gute Verteilung. Geringe Kardinalität oder monoton wachsende Werte können Hotspots erzeugen; das Feld muss außerdem in jedem Dokument der geshardeten Collection existieren.",
        "Having a shard key does not guarantee good distribution. Low cardinality or monotonically increasing values can create hotspots, and the field must exist in every document of the sharded collection.",
    ),
    "Manifest": multilingual(
        "Das Manifest enthält Metadaten über gültige SSTables, nicht die eigentlichen Nutzdaten. Es darf nicht mit WAL oder SSTable verwechselt werden.",
        "The manifest stores metadata about valid SSTables, not the user data itself. It is not the WAL or an SSTable.",
    ),
    "Index-Free Adjacency": multilingual(
        "Index-free adjacency beschleunigt lokale Nachbarschaftstraversierung, garantiert aber keine konstante Laufzeit für beliebig große Pfadsuchen. Der besuchte Teilgraph bleibt entscheidend.",
        "Index-free adjacency speeds up local neighbor traversal but does not guarantee constant time for arbitrary path searches. The visited subgraph still matters.",
    ),
    "Node Key": multilingual(
        "Ein Node Key ist stärker als reine Eindeutigkeit: Die beteiligten Properties müssen sowohl vorhanden als auch in ihrer Kombination eindeutig sein.",
        "A node key is stronger than uniqueness alone: its properties must both exist and be unique as a combination.",
    ),
    "Inconsistency Window": multilingual(
        "Das Inconsistency Window ist keine zugesicherte feste Zeitspanne. Seine Dauer hängt unter anderem von Replikationsverzögerung, Ausfällen und Last ab.",
        "The inconsistency window is not a guaranteed fixed duration. It depends on replication delay, failures, and load.",
    ),
    "Optimistic Conflict Resolution": multilingual(
        "Optimistisch bedeutet nicht konfliktfrei. Anwendungen müssen konkurrierende Versionen erkennen und fachlich korrekt zusammenführen oder eine Version bewusst verwerfen.",
        "Optimistic does not mean conflict-free. Applications must detect concurrent versions and merge them correctly or deliberately discard one.",
    ),
    "Pessimistic Conflict Prevention": multilingual(
        "Sperren verhindern Konflikte vorab, können aber Wartezeiten, Deadlocks und geringere Verfügbarkeit verursachen. Konfliktfreiheit ist nicht kostenlos.",
        "Locks prevent conflicts in advance but may cause waiting, deadlocks, and reduced availability. Conflict prevention is not free.",
    ),
    "Log-Structured Storage": multilingual(
        "Append-only macht Writes billig, entfernt aber alte Versionen nicht automatisch. Ohne Merge oder Compaction wachsen Speicherbedarf und Read-Kosten.",
        "Append-only makes writes cheap but does not remove old versions automatically. Without merge or compaction, space and read costs grow.",
    ),
    "Active Data File": multilingual(
        "In Bitcask ist genau eine Datendatei aktiv beschreibbar. Alte Dateien werden für Updates nicht erneut geöffnet.",
        "Exactly one Bitcask data file is active for writes. Older files are not reopened for updates.",
    ),
    "Immutable Data File": multilingual(
        "Immutable bedeutet unveränderlich, nicht unlesbar oder sofort löschbar. Lebende Keydir-Einträge können weiterhin auf diese Datei zeigen.",
        "Immutable means unchangeable, not unreadable or immediately deletable. Live keydir entries may still reference the file.",
    ),
    "Put Operation": multilingual(
        "Ein Put überschreibt bei log-strukturierter Speicherung den alten Eintrag nicht in-place. Er erzeugt eine neue Version und aktualisiert den Index.",
        "In log-structured storage, put does not overwrite the old record in place. It creates a new version and updates the index.",
    ),
    "Get Operation": multilingual(
        "Ein Get darf nicht einfach den ersten gefundenen physischen Eintrag verwenden. Entscheidend ist die neueste durch Index oder Versionsinformation bestimmte Version.",
        "A get cannot simply use the first physical record found. It must return the newest version identified by the index or version metadata.",
    ),
    "Merge Process": multilingual(
        "Merge und normale Writes sind getrennt: Neue Client-Writes gehen weiter in die aktive Datei, während der Merge geschlossene Dateien bereinigt.",
        "Merge is separate from normal writes: new client writes continue into the active file while merge cleans closed files.",
    ),
    "Sparse Index": multilingual(
        "Ein Sparse Index zeigt nur auf einen möglichen Block, nicht zwingend direkt auf den gesuchten Record. Innerhalb des Blocks ist eine weitere Suche nötig.",
        "A sparse index points to a candidate block, not necessarily directly to the requested record. The block still needs to be searched.",
    ),
    "Delete Operation": multilingual(
        "Ein Tombstone darf nicht zu früh entfernt werden. Existiert in einer tieferen Datei noch ein alter Wert, könnte dieser sonst nach der Compaction wieder sichtbar werden.",
        "A tombstone must not be removed too early. If an older value remains in a lower file, it could otherwise become visible again after compaction.",
    ),
    "BSON Document Limit": multilingual(
        "Die 16-MB-Grenze gilt pro Dokument, nicht für die gesamte Collection. Viele kleine Dokumente dürfen zusammen weit größer sein.",
        "The 16 MB limit applies per document, not to the whole collection. Many small documents may be much larger in total.",
    ),
    "Array of References": multilingual(
        "Eine unbegrenzt wachsende Referenzliste kann selbst zum großen, häufig geänderten Dokument werden und an die 16-MB-Grenze stoßen.",
        "An unbounded reference array can itself become a large frequently updated document and approach the 16 MB limit.",
    ),
    "Document Validation": multilingual(
        "Validierung macht MongoDB nicht zu einem starren relationalen Schema. Regeln können partiell sein und müssen bei Schema-Evolution bewusst angepasst werden.",
        "Validation does not turn MongoDB into a rigid relational schema. Rules may be partial and must be evolved deliberately.",
    ),
    "Existence Constraint": multilingual(
        "Ein Existence Constraint verlangt nur das Vorhandensein einer Property; er macht deren Wert nicht automatisch eindeutig.",
        "An existence constraint requires a property to be present; it does not make the value unique.",
    ),
    "Relationship Type": multilingual(
        "Relationship Type und Richtung sind getrennte Eigenschaften. Eine ungerichtete Query ignoriert die Richtung beim Match, ändert aber nicht den gespeicherten Typ oder die gespeicherte Richtung.",
        "Relationship type and direction are separate. An undirected query ignores direction while matching but does not alter the stored type or direction.",
    ),
    "Variable-Length Path": multilingual(
        "Ein unbeschränktes * kann einen sehr großen Suchraum erzeugen. Außerdem beschreibt die Zahl Beziehungen, nicht Knoten oder Zwischenstopps.",
        "An unbounded * can create a very large search space. Its number counts relationships, not nodes or intermediate stops.",
    ),
    "Zero-Length Path": multilingual(
        "Bei *0..n kann der Startknoten selbst Teil des Ergebnisses sein. Wer nur tatsächlich durchlaufene Beziehungen erwartet, übersieht diesen Fall.",
        "With *0..n, the start node itself may be a result. This is easy to miss when expecting at least one traversed relationship.",
    ),
    "Vertical Fragmentation": multilingual(
        "Nach der Aufteilung muss die Zeilenzugehörigkeit erhalten bleiben. Ohne explizite IDs oder stabile virtuelle Positionen lassen sich Spaltenwerte nicht korrekt zu Tupeln zusammensetzen.",
        "After splitting columns, row identity must remain available. Without explicit IDs or stable virtual positions, values cannot be reconstructed into correct tuples.",
    ),
    "Dictionary Encoding": multilingual(
        "Ein Dictionary verursacht eigenen Speicher- und Lookup-Aufwand. Bei fast nur eindeutigen kurzen Werten kann es mehr kosten als es spart.",
        "A dictionary has its own storage and lookup cost. With mostly unique short values, it may cost more than it saves.",
    ),
    "Null Suppression": multilingual(
        "Wer NULL-Werte weglässt, muss ihre ursprünglichen Positionen weiterhin rekonstruieren können. Sonst verschieben sich die Zuordnungen zu anderen Spalten.",
        "When nulls are omitted, their original positions must remain recoverable; otherwise alignment with other columns is lost.",
    ),
    "Virtual ID": multilingual(
        "Virtuelle IDs funktionieren nur, solange Positionen stabil und effizient bestimmbar sind. Variable Breite oder nicht längenerhaltende Kompression kann diese Annahme brechen.",
        "Virtual IDs work only while positions remain stable and efficiently computable. Variable width or non-length-preserving compression can break that assumption.",
    ),
    "Schemaless": multilingual(
        "Schemaless bedeutet nicht, dass keine Struktur existiert. Das Schema liegt häufig implizit im Anwendungscode und Fehler werden später statt beim Write entdeckt.",
        "Schemaless does not mean structureless. The schema often lives implicitly in application code and errors are detected later instead of on write.",
    ),
    "Schema-on-Read": multilingual(
        "Schema-on-Read verschiebt Validierung und Interpretationskosten auf jeden Leser. Unterschiedliche Leser können dieselben Rohdaten sonst widersprüchlich deuten.",
        "Schema-on-read shifts validation and interpretation cost to every reader. Different readers may otherwise interpret the same raw data inconsistently.",
    ),
    "Application Database": multilingual(
        "Anwendungsspezifische Datenbanken erleichtern Optimierung, können aber Daten duplizieren und systemübergreifende Integration erschweren.",
        "Application-specific databases simplify optimization but may duplicate data and make cross-system integration harder.",
    ),
    "Integration Database": multilingual(
        "Ein gemeinsames Schema koppelt viele Anwendungen. Änderungen benötigen mehr Abstimmung und die Datenbank lässt sich schwerer für einen einzelnen Workload optimieren.",
        "A shared schema couples many applications. Changes require more coordination and the database is harder to optimize for one workload.",
    ),
    "Network Partition": multilingual(
        "Eine Partition ist ein Kommunikationsausfall, nicht zwingend ein Knotenausfall. Knoten auf beiden Seiten können weiterlaufen und lokale Anfragen erhalten.",
        "A partition is a communication failure, not necessarily a node failure. Nodes on both sides may keep running and receive local requests.",
    ),
    "Explicit ID": multilingual(
        "Explizite IDs erleichtern Rekonstruktion, vergrößern aber jede Spalte und erhöhen I/O. Dieser Platz-Trade-off fehlt bei virtuellen IDs.",
        "Explicit IDs simplify reconstruction but enlarge every column and increase I/O. Virtual IDs avoid that space cost.",
    ),
    "Bitmap Index": multilingual(
        "Bitmap-Indizes passen besonders zu kleiner Domäne. Bei sehr vielen unterschiedlichen Werten entstehen zu viele dünn besetzte Bitvektoren.",
        "Bitmap indexes fit low-cardinality domains. With many distinct values, they create too many sparsely populated bit vectors.",
    ),
    "Position List": multilingual(
        "Eine Positionsliste enthält Positionen, nicht automatisch die zugehörigen Werte. Für Projektion oder Ausgabe ist meist noch reconstruct nötig.",
        "A position list contains positions, not automatically the corresponding values. Projection or output usually still requires reconstruct.",
    ),
    "Read Store": multilingual(
        "Read Store bedeutet nicht, dass dort niemals Änderungen ankommen. Sie werden nur meist gesammelt aus dem Write Store übernommen, statt jede Einzeländerung direkt in die komprimierte Hauptstruktur einzubauen.",
        "Read store does not mean changes never reach it. Updates are usually transferred in batches from the write store instead of modifying the compressed main structure one by one.",
    ),
    "Write Store": multilingual(
        "Der Write Store ersetzt den Read Store nicht. Abfragen müssen beide Bereiche berücksichtigen, sonst fehlen die neuesten noch nicht zusammengeführten Änderungen.",
        "The write store does not replace the read store. Queries must consider both areas or they will miss recent changes that have not yet been merged.",
    ),
}

BEGINNER_EXPLANATIONS = {
    "ACID": multilingual(
        "ACID ist eine Sicherheitscheckliste für Datenbankvorgänge. Sie sorgt vereinfacht dafür, dass zusammengehörige Änderungen ganz oder gar nicht passieren, keine ungültigen Daten erzeugen, sich bei gleichzeitiger Ausführung nicht unkontrolliert stören und nach dem Speichern erhalten bleiben.",
        "ACID is a safety checklist for database operations. Related changes happen completely or not at all, preserve valid data, do not interfere uncontrollably when run concurrently, and remain stored after confirmation.",
    ),
    "Aggregate": multilingual(
        "Ein Aggregat ist ein Datenpaket, das die Datenbank meistens gemeinsam behandelt. Zum Beispiel können eine Bestellung und ihre Positionen zusammen gelesen, gespeichert und auf denselben Server gelegt werden.",
        "An aggregate is a package of data that the database usually handles together. For example, an order and its line items may be read, stored, and placed on one server as a unit.",
    ),
    "AP-System": multilingual(
        "Wenn Server wegen eines Netzfehlers nicht miteinander sprechen können, antwortet ein AP-System trotzdem weiter. Dafür nimmt es in Kauf, dass verschiedene Server vorübergehend unterschiedliche Datenstände haben.",
        "When servers cannot communicate because of a network failure, an AP system keeps answering. In return, different servers may temporarily hold different versions of the data.",
    ),
    "BASE": multilingual(
        "BASE beschreibt Systeme, die lieber erreichbar und schnell bleiben, auch wenn nicht sofort überall derselbe Datenstand sichtbar ist. Wenn keine neuen Änderungen kommen, sollen sich die Kopien später wieder angleichen.",
        "BASE describes systems that prefer to remain reachable and fast even when every copy does not immediately show the same data. Without further updates, the copies should converge later.",
    ),
    "CAP-Theorem": multilingual(
        "Wenn ein verteiltes System in getrennte Servergruppen zerfällt, muss es sich entscheiden: Entweder antwortet jede Gruppe weiter oder alle Antworten bleiben garantiert auf demselben aktuellen Stand. Beides gleichzeitig ist dann nicht vollständig möglich.",
        "When a distributed system splits into server groups that cannot communicate, it must choose: either every group keeps answering or all answers are guaranteed to reflect one current state. It cannot fully guarantee both.",
    ),
    "Causal Consistency": multilingual(
        "Ursache und Folge müssen überall in der richtigen Reihenfolge erscheinen. Wer eine Antwort auf einen Beitrag sieht, muss also auch den ursprünglichen Beitrag sehen; unabhängige Beiträge dürfen unterschiedlich sortiert sein.",
        "Cause and effect must appear in the correct order everywhere. Anyone seeing a reply must also see the original post, while unrelated posts may be ordered differently.",
    ),
    "CP-System": multilingual(
        "Wenn Server wegen eines Netzfehlers getrennt sind, gibt ein CP-System lieber zeitweise keine Antwort, als möglicherweise veraltete oder widersprüchliche Daten zu liefern.",
        "When servers are separated by a network failure, a CP system prefers to reject or delay some requests rather than return possibly stale or conflicting data.",
    ),
    "Eventual Consistency": multilingual(
        "Mehrere Datenkopien dürfen kurz unterschiedlich sein. Wenn danach niemand mehr etwas ändert, werden sie irgendwann wieder gleich; wie lange das dauert, ist damit nicht festgelegt.",
        "Several copies may temporarily differ. If no more updates occur, they will eventually become equal again, but the model does not specify how long that takes.",
    ),
    "Happened-Before": multilingual(
        "Happened-Before bedeutet: Ein Ereignis kann ein anderes beeinflusst haben, weil es vorher im selben Prozess geschah oder eine Nachricht dorthin geschickt hat. Unabhängige Ereignisse haben keine solche Reihenfolge.",
        "Happened-before means one event could have influenced another because it occurred earlier in the same process or sent a message leading to it. Independent events have no such order.",
    ),
    "Lamport Clock": multilingual(
        "Eine Lamport-Uhr ist kein echter Zeitmesser, sondern eine hochzählende Nummer für Ereignisse. Sie stellt sicher, dass eine Ursache eine kleinere Nummer als ihre Folge erhält, erkennt aber unabhängige Ereignisse nicht zuverlässig.",
        "A Lamport clock is not a wall clock but an increasing event number. It ensures that a cause receives a smaller number than its effect, but it cannot reliably detect independent events.",
    ),
    "PACELC": multilingual(
        "PACELC betrachtet zwei Situationen: Bei einem Netzwerkausfall muss zwischen Erreichbarkeit und gleichem Datenstand gewählt werden; im Normalbetrieb zwischen schneller Antwort und stärkerer Konsistenz.",
        "PACELC considers two situations: during a network failure, choose between availability and a consistent state; during normal operation, choose between lower latency and stronger consistency.",
    ),
    "Quorum Consensus": multilingual(
        "Beim Quorum reicht nicht die Antwort eines beliebigen Servers. Ein Read oder Write muss genügend Datenkopien erreichen, damit sich die beteiligten Servermengen überschneiden und der aktuelle Stand gefunden wird.",
        "With quorums, one arbitrary server is not enough. A read or write must contact enough replicas so the participating sets overlap and the current version can be found.",
    ),
    "Single-Copy Consistency": multilingual(
        "Obwohl mehrere Datenkopien existieren, soll es für Benutzer so aussehen, als gäbe es nur eine einzige, immer eindeutig aktuelle Datenbank.",
        "Although several copies exist, users should experience the system as if there were one single, unambiguously current database.",
    ),
    "Vector Clock": multilingual(
        "Eine Vektoruhr führt für jeden beteiligten Server einen eigenen Zähler. Dadurch kann sie erkennen, ob eine Änderung auf einer anderen aufbaut oder ob beide unabhängig gleichzeitig entstanden sind.",
        "A vector clock keeps one counter per participating server. It can therefore detect whether one update depends on another or whether both were created independently and concurrently.",
    ),
    "Bitcask": multilingual(
        "Bitcask speichert jede Änderung einfach am Ende einer Datei und merkt sich im Arbeitsspeicher, wo die neueste Version jedes Schlüssels liegt. Schreiben ist dadurch schnell und Lesen benötigt einen gezielten Dateizugriff.",
        "Bitcask appends every change to a file and remembers in memory where the newest version of each key is stored. Writes are fast and reads need one targeted file access.",
    ),
    "Bloom Filter": multilingual(
        "Ein Bloom-Filter ist ein sehr platzsparender Vorabtest. Er kann sicher sagen, dass ein Schlüssel nicht in einer Datei liegt; bei einem positiven Ergebnis muss die Datei aber trotzdem geprüft werden.",
        "A Bloom filter is a compact preliminary test. It can safely say that a key is not in a file, but a positive result still requires checking the file.",
    ),
    "Compaction": multilingual(
        "Compaction räumt die vielen Dateien eines log-strukturierten Speichers auf. Dabei werden Dateien zusammengeführt und alte Versionen oder gelöschte Werte entfernt.",
        "Compaction cleans up the many files of log-structured storage by merging them and removing obsolete versions or deleted values.",
    ),
    "Fence Pointer": multilingual(
        "Ein Fence Pointer ist wie ein Wegweiser am Anfang eines Datenblocks. Er sagt, bei welchem Schlüssel der Block beginnt und wo er in der Datei liegt, damit nicht die ganze Datei durchsucht werden muss.",
        "A fence pointer is like a signpost at the start of a data block. It records the block's first key and file location so the entire file need not be searched.",
    ),
    "Flush": multilingual(
        "Beim Flush wird eine volle, bereits eingefrorene Arbeitsspeicher-Tabelle dauerhaft als neue sortierte Datei auf die Festplatte geschrieben. Andere Dateien werden dabei noch nicht aufgeräumt.",
        "During flush, a full frozen in-memory table is written permanently as a new sorted disk file. Existing files are not reorganized yet.",
    ),
    "LSM-Tree": multilingual(
        "Ein LSM-Tree sammelt neue Änderungen zuerst schnell im Arbeitsspeicher und schreibt sie später gebündelt in sortierte Dateien. Das beschleunigt viele Writes, macht Reads und Aufräumen aber aufwendiger.",
        "An LSM-tree first collects new changes quickly in memory and later writes them in batches to sorted files. This speeds up writes but makes reads and cleanup more involved.",
    ),
    "Manifest": multilingual(
        "Das Manifest ist das Inhaltsverzeichnis eines LSM-Stores. Es hält fest, welche sortierten Dateien aktuell dazugehören und welche nach einer Compaction ersetzt wurden.",
        "The manifest is the table of contents of an LSM store. It records which sorted files currently belong to the store and which were replaced by compaction.",
    ),
    "Memtable": multilingual(
        "Eine Memtable ist die aktuelle sortierte Zwischenspeicherung im Arbeitsspeicher. Neue Änderungen landen dort zuerst, bevor sie als SSTable auf die Festplatte geschrieben werden.",
        "A memtable is the current sorted buffer in memory. New changes enter it first before being written to disk as an SSTable.",
    ),
    "SSTable": multilingual(
        "Eine SSTable ist eine unveränderliche Datei, deren Schlüssel sortiert sind. Weil sie nach dem Schreiben nicht mehr geändert wird, kann sie effizient gelesen und später mit anderen SSTables zusammengeführt werden.",
        "An SSTable is an immutable file with sorted keys. Because it is not changed after creation, it can be read efficiently and later merged with other SSTables.",
    ),
    "Tombstone": multilingual(
        "Ein Tombstone ist ein Löschzettel. Statt einen alten Wert sofort aus allen Dateien zu entfernen, wird zunächst vermerkt, dass dieser Schlüssel als gelöscht gelten soll.",
        "A tombstone is a deletion marker. Instead of immediately removing an old value from every file, the system records that the key must be treated as deleted.",
    ),
    "Write-Ahead Log": multilingual(
        "Das Write-Ahead Log ist ein Sicherheitsprotokoll. Eine Änderung wird dort dauerhaft notiert, bevor sie nur im flüchtigen Arbeitsspeicher landet, damit sie nach einem Absturz wiederhergestellt werden kann.",
        "A write-ahead log is a safety journal. A change is recorded persistently before it exists only in volatile memory so it can be recovered after a crash.",
    ),
    "Read Amplification": multilingual(
        "Read Amplification bedeutet, dass für eine einzige gewünschte Antwort mehrere Dateien oder Datenkopien geprüft werden müssen.",
        "Read amplification means that several files or copies must be checked to answer one logical read.",
    ),
    "Write Amplification": multilingual(
        "Write Amplification bedeutet, dass intern deutlich mehr Daten geschrieben werden als die Anwendung eigentlich geändert hat, etwa durch Log, Flush und wiederholte Compactions.",
        "Write amplification means the system physically writes much more data than the application changed, for example through logging, flushes, and repeated compactions.",
    ),
    "Denormalization": multilingual(
        "Bei Denormalisierung werden Informationen absichtlich mehrfach gespeichert. Dadurch werden Reads einfacher und schneller, aber Änderungen müssen an mehreren Stellen korrekt nachgezogen werden.",
        "Denormalization deliberately stores information more than once. Reads become simpler and faster, but updates must be applied correctly in several places.",
    ),
    "Embedding": multilingual(
        "Embedding bedeutet, ein abhängiges Objekt direkt in ein anderes Dokument hineinzuschreiben, etwa Adressdaten in ein Kundendokument. Beides kann dann gemeinsam gelesen und oft atomar geändert werden.",
        "Embedding means storing a dependent object directly inside another document, such as an address inside a customer document. Both can then be read together and often changed atomically.",
    ),
    "Read Concern": multilingual(
        "Read Concern bestimmt, wie verlässlich oder bestätigt der gelesene Datenstand sein muss. Es beantwortet nicht, von welchem Server gelesen wird, sondern welche Qualität der sichtbare Stand haben soll.",
        "Read concern determines how reliable or confirmed the visible data must be. It does not choose the server; it chooses the required quality of the read view.",
    ),
    "Read Preference": multilingual(
        "Read Preference bestimmt, von welchem Mitglied eines MongoDB Replica Sets gelesen werden soll, zum Beispiel bevorzugt vom Primary oder von einem Secondary.",
        "Read preference chooses which MongoDB replica-set member should serve a read, for example the primary or preferably a secondary.",
    ),
    "Write Concern": multilingual(
        "Write Concern bestimmt, wie viele Server beziehungsweise welche dauerhafte Speicherung einen Write bestätigen müssen, bevor MongoDB ihn als erfolgreich meldet.",
        "Write concern determines how many servers or which durable storage must acknowledge a write before MongoDB reports success.",
    ),
    "MERGE": multilingual(
        "MERGE bedeutet in Cypher: Suche zuerst nach genau diesem vollständigen Muster; nur wenn es nicht existiert, wird es neu angelegt. Es ist deshalb kein allgemeiner Befehl zum Aktualisieren nach Namen.",
        "MERGE in Cypher means: first search for this exact complete pattern and create it only if no match exists. It is therefore not a general update-by-name command.",
    ),
    "Index-Free Adjacency": multilingual(
        "Ein Graphknoten kennt seine direkten Nachbarn über gespeicherte Verweise. Die Datenbank kann einer Beziehung deshalb direkt folgen, statt zuerst über eine große Tabelle passende IDs zusammenzusuchen.",
        "A graph node knows its direct neighbors through stored references. The database can follow a relationship directly instead of joining IDs through a large table.",
    ),
    "Relationship Uniqueness": multilingual(
        "Innerhalb eines einzelnen Cypher-Musters darf dieselbe konkrete Kante nicht zweimal für zwei Pattern-Stellen verwendet werden. Verschiedene Kanten desselben Typs sind dagegen erlaubt.",
        "Within one Cypher pattern, the same stored edge cannot fill two relationship positions. Different edges of the same type are allowed.",
    ),
    "Variable-Length Path": multilingual(
        "Ein Variable-Length Path erlaubt unterschiedlich viele aufeinanderfolgende Beziehungen. *1..3 bedeutet zum Beispiel: Der Weg darf eine, zwei oder drei Kanten lang sein.",
        "A variable-length path allows different numbers of consecutive relationships. For example, *1..3 means the path may contain one, two, or three edges.",
    ),
    "Zero-Length Path": multilingual(
        "Ein Pfad der Länge null geht nirgendwohin: Start- und Zielknoten sind derselbe Knoten und es wird keine Beziehung durchlaufen.",
        "A zero-length path goes nowhere: start and target are the same node and no relationship is traversed.",
    ),
    "WITH": multilingual(
        "WITH ist in Cypher eine Zwischenstation. Es gibt ausgewählte oder berechnete Ergebnisse an den nächsten Teil der Query weiter, ähnlich einer benannten Zwischentabelle.",
        "WITH is an intermediate stage in Cypher. It passes selected or calculated results to the next query part, similar to a named temporary table.",
    ),
    "Column Store": multilingual(
        "Ein Column Store legt alle Werte einer Spalte zusammen ab, also zum Beispiel alle Preise getrennt von allen Produktnamen. Analysen, die nur wenige Spalten brauchen, müssen dadurch weniger Daten lesen.",
        "A column store keeps all values of one column together, such as all prices separately from product names. Analytics using only a few columns can read less data.",
    ),
    "Dictionary Encoding": multilingual(
        "Dictionary Encoding ersetzt häufig wiederholte oder lange Werte durch kurze Nummern. Statt jedes Mal „Österreich“ zu speichern, steht in der Spalte etwa nur die ID 7.",
        "Dictionary encoding replaces repeated or long values with short numbers. Instead of storing “Austria” repeatedly, the column may store only ID 7.",
    ),
    "Early Materialization": multilingual(
        "Bei Early Materialization werden getrennt gespeicherte Spalten früh wieder zu vollständigen Zeilen zusammengesetzt, auch wenn später vielleicht viele dieser Zeilen herausgefiltert werden.",
        "With early materialization, separately stored columns are rebuilt into full rows early, even if many rows may later be filtered out.",
    ),
    "Late Materialization": multilingual(
        "Bei Late Materialization bleiben Spalten möglichst lange getrennt. Erst nachdem Filter und Joins viele Zeilen ausgeschlossen haben, werden die benötigten Werte zu Ergebnissen zusammengesetzt.",
        "With late materialization, columns remain separate as long as possible. Values are combined only after filters and joins have removed many rows.",
    ),
    "Run-Length Encoding": multilingual(
        "Run-Length Encoding fasst gleiche Werte hintereinander zusammen. Aus A,A,A,A,B,B wird beispielsweise A viermal und B zweimal.",
        "Run-length encoding groups equal consecutive values. For example, A,A,A,A,B,B becomes A four times and B two times.",
    ),
    "SIMD": multilingual(
        "SIMD bedeutet, dass der Prozessor dieselbe Rechenoperation gleichzeitig auf mehrere Werte anwendet, etwa vier Preise parallel addiert statt nacheinander.",
        "SIMD means the processor applies one operation to several values at once, such as adding four prices in parallel instead of one after another.",
    ),
    "Virtual ID": multilingual(
        "Bei einer Virtual ID ist die Position eines Werts seine Kennung. Der 17. Wert jeder Spalte gehört dann zur 17. logischen Zeile, ohne dass die Zahl 17 extra gespeichert wird.",
        "With a virtual ID, a value's position is its identifier. The 17th value in every column belongs to logical row 17 without storing the number 17 explicitly.",
    ),
    "Wide Column Store": multilingual(
        "Ein Wide Column Store organisiert Daten nach Zeilenschlüssel und flexiblen Spalten. Verschiedene Zeilen dürfen unterschiedliche Spalten besitzen, und eine Zelle kann mehrere zeitliche Versionen haben.",
        "A wide-column store organizes data by row key and flexible columns. Different rows may have different columns, and a cell may keep several time-based versions.",
    ),
    "Materialization": multilingual(
        "Materialisierung setzt Werte aus getrennt gespeicherten Spalten wieder zu zusammengehörigen Zeilen oder Ergebnissen zusammen.",
        "Materialization combines values from separately stored columns back into matching rows or result records.",
    ),
    "reconstruct": multilingual(
        "reconstruct erhält eine Liste von Zeilenpositionen und holt aus einer bestimmten Spalte genau die Werte an diesen Positionen nach.",
        "reconstruct receives a list of row positions and fetches exactly the values at those positions from a chosen column.",
    ),
    "reverse": multilingual(
        "reverse vertauscht in jedem Paar die beiden Seiten. Aus (Position, Wert) wird (Wert, Position), damit beispielsweise über den Wert gejoint werden kann.",
        "reverse swaps the two sides of every pair. It turns (position, value) into (value, position), for example to join by value.",
    ),
    "voidTail": multilingual(
        "voidTail entfernt aus jedem Paar den zweiten Teil. Aus (Position links, Position rechts) bleibt nur die linke Position übrig.",
        "voidTail removes the second part of every pair. From (left position, right position), only the left position remains.",
    ),
}

BEGINNER_EXPLANATIONS.update(
    {
        "Monotonic Reads": multilingual(
            "Sobald du in einer Sitzung einen bestimmten Datenstand gesehen hast, darfst du später nicht wieder eine ältere Version bekommen. Deine Sicht bewegt sich also nur vorwärts.",
            "Once a session has seen a particular data version, it must not later receive an older one. Its view only moves forward.",
        ),
        "Read-Your-Writes": multilingual(
            "Wenn du selbst etwas gespeichert hast und direkt danach wieder liest, musst du mindestens deine eigene Änderung sehen und darfst nicht auf einen älteren Stand zurückfallen.",
            "After you save something and immediately read again, you must see at least your own change rather than an older version.",
        ),
        "Replication": multilingual(
            "Replikation bedeutet, dieselben Daten mehrfach auf verschiedenen Servern zu speichern. Fällt eine Kopie aus, kann eine andere übernehmen; die Kopien können aber kurz unterschiedlich aktuell sein.",
            "Replication stores the same data on several servers. Another copy can take over after a failure, although copies may briefly have different versions.",
        ),
        "ROWA": multilingual(
            "Bei Read One, Write All reicht zum Lesen eine Kopie, aber ein Write muss alle N Kopien erreichen. Lesen ist dadurch leicht, Schreiben hängt jedoch von jedem Replikat ab.",
            "With read one, write all, one replica is enough for a read, but a write must reach all N replicas. Reads are easy, while writes depend on every replica.",
        ),
        "Sharding": multilingual(
            "Sharding verteilt verschiedene Teile der Daten auf verschiedene Server. Zum Beispiel liegen Kunden A–M auf Server 1 und N–Z auf Server 2; es entstehen keine bloßen Kopien derselben Daten.",
            "Sharding distributes different parts of the data across servers. Customers A–M may be on server 1 and N–Z on server 2; these are not copies of the same data.",
        ),
        "Schemaless": multilingual(
            "Schemaless heißt, dass nicht jedes gespeicherte Objekt exakt dieselben Felder haben muss. Die Anwendung muss trotzdem wissen, welche Struktur sie erwartet.",
            "Schemaless means not every stored object must have exactly the same fields. The application still needs to know which structure it expects.",
        ),
        "Schema-on-Read": multilingual(
            "Die Daten werden zunächst flexibel gespeichert. Erst beim Lesen entscheidet die Anwendung, welche Felder und Datentypen sie erwartet und wie ältere Varianten behandelt werden.",
            "Data is stored flexibly first. When reading, the application decides which fields and types it expects and how older variants are interpreted.",
        ),
        "Application Database": multilingual(
            "Eine Application Database wird für die Bedürfnisse genau einer Anwendung gebaut, etwa eine Graphdatenbank nur für Empfehlungen. Dadurch kann sie sehr passend optimiert werden.",
            "An application database is built for one application's needs, such as a graph database used only for recommendations, allowing focused optimization.",
        ),
        "Integration Database": multilingual(
            "Eine Integration Database ist eine gemeinsame Datenbasis für mehrere Anwendungen. Sie soll Informationen zentral zusammenhalten, muss deshalb aber viele unterschiedliche Anforderungen erfüllen.",
            "An integration database is a shared data source for several applications. It centralizes information but must satisfy many different requirements.",
        ),
        "Availability": multilingual(
            "Availability im CAP-Sinn heißt: Jeder erreichbare, nicht ausgefallene Server muss auf jede Anfrage antworten. Die Antwort darf dabei im AP-Fall auch einen nicht ganz aktuellen Stand enthalten.",
            "CAP availability means every reachable non-failing server must answer every request. In an AP system, that answer may contain a not fully current version.",
        ),
        "Partition Tolerance": multilingual(
            "Das System arbeitet weiter, obwohl Teile des Netzwerks nicht miteinander kommunizieren können. Es muss dann festlegen, ob es eher Antworten oder einen überall gleichen Datenstand bevorzugt.",
            "The system keeps operating even when parts of the network cannot communicate. It must then decide whether to favor responses or one consistent state.",
        ),
        "Network Partition": multilingual(
            "Bei einer Network Partition laufen Server weiter, können aber bestimmte andere Server vorübergehend nicht erreichen. Dadurch entstehen getrennte Gruppen mit unvollständigem Wissen.",
            "During a network partition, servers keep running but temporarily cannot reach some other servers, creating separated groups with incomplete knowledge.",
        ),
        "Inconsistency Window": multilingual(
            "Das Inconsistency Window ist die Zeit zwischen einer Änderung und dem Moment, an dem alle Datenkopien diese Änderung übernommen haben.",
            "The inconsistency window is the time between an update and the moment every replica has applied it.",
        ),
        "Version Stamp": multilingual(
            "Ein Version Stamp ist ein Zusatz an einem Datenwert, der zeigt, zu welcher Version er gehört. Damit kann das System erkennen, welche von mehreren Kopien neuer ist oder ob Konflikte bestehen.",
            "A version stamp is metadata attached to a value that identifies its version. It helps determine which copy is newer or whether versions conflict.",
        ),
        "Optimistic Conflict Resolution": multilingual(
            "Das System lässt gleichzeitige Änderungen zunächst zu und löst mögliche Widersprüche später. Das ist sinnvoll, wenn Konflikte selten sind oder fachlich zusammengeführt werden können.",
            "The system initially allows concurrent changes and resolves contradictions later. This works when conflicts are rare or can be merged meaningfully.",
        ),
        "Pessimistic Conflict Prevention": multilingual(
            "Das System verhindert mögliche Konflikte schon vor dem Schreiben, etwa durch Sperren. Andere Zugriffe müssen dann warten, dafür entstehen keine zwei konkurrierenden Versionen.",
            "The system prevents possible conflicts before writing, for example with locks. Other accesses wait, avoiding competing versions.",
        ),
        "Monotonic Writes": multilingual(
            "Mehrere Änderungen derselben Sitzung müssen überall in der Reihenfolge ankommen, in der sie abgeschickt wurden. Die zweite Änderung darf nicht vor der ersten sichtbar werden.",
            "Several writes from one session must be observed in the order they were issued. The second write must not appear before the first.",
        ),
        "Writes Follow Reads": multilingual(
            "Wenn ein neuer Write auf zuvor gelesenen Daten beruht, bleibt diese Abhängigkeit erhalten. Wer den neuen Write sieht, muss auch den zugrunde liegenden Datenstand kennen.",
            "When a new write is based on previously read data, that dependency is preserved. Anyone seeing the write must also see the data it was based on.",
        ),
    }
)

BEGINNER_EXPLANATIONS.update(
    {
        "Hint File": multilingual(
            "Eine Hint File ist ein kompakter Wegweiser zu den Einträgen einer Bitcask-Datei. Beim Neustart kann Bitcask daraus die Keydir schneller aufbauen, ohne jeden vollständigen Wert lesen zu müssen.",
            "A hint file is a compact guide to the records in a Bitcask file. On restart, Bitcask can rebuild keydir without reading every complete value.",
        ),
        "Keydir": multilingual(
            "Die Keydir ist Bitcasks Inhaltsverzeichnis im Arbeitsspeicher. Für jeden Schlüssel steht dort, in welcher Datei und an welcher Stelle seine neueste Version liegt.",
            "Keydir is Bitcask's in-memory table of contents. For every key, it records the file and position of the newest version.",
        ),
        "Leveling": multilingual(
            "Beim Leveling werden Dateien häufig zusammengeführt, sodass sich Schlüsselbereiche in höheren Levels nicht überschneiden. Reads werden einfacher, dafür werden Daten öfter neu geschrieben.",
            "With leveling, files are merged so key ranges do not overlap within higher levels. Reads become easier, but data is rewritten more often.",
        ),
        "Tiering": multilingual(
            "Beim Tiering dürfen mehrere Dateien mit überlappenden Schlüsselbereichen auf einem Level bleiben. Writes benötigen weniger Aufräumarbeit, Reads müssen dafür mehr Dateien prüfen.",
            "With tiering, several files with overlapping key ranges may remain on one level. Writes need less cleanup, while reads must inspect more files.",
        ),
        "Point Query": multilingual(
            "Eine Point Query sucht genau einen Schlüssel, etwa user:42. Sie unterscheidet sich von einer Bereichsabfrage, die viele aufeinanderfolgende Schlüssel lesen kann.",
            "A point query looks up exactly one key, such as user:42. It differs from a range query that reads many consecutive keys.",
        ),
        "Log-Structured Storage": multilingual(
            "Änderungen werden nicht an ihrer alten Stelle überschrieben, sondern immer hinten angehängt. Ein Index zeigt auf die neueste Version; alte Versionen werden später aufgeräumt.",
            "Changes are appended instead of overwriting old locations. An index points to the newest version, while old versions are cleaned up later.",
        ),
        "Active Data File": multilingual(
            "Die Active Data File ist die eine Bitcask-Datei, an deren Ende gerade neue Writes angehängt werden. Alle älteren Dateien sind bereits geschlossen.",
            "The active data file is the one Bitcask file currently receiving new appended writes. All older files are closed.",
        ),
        "Immutable Data File": multilingual(
            "Eine Immutable Data File ist eine geschlossene Datei, die nicht mehr verändert wird. Sie bleibt lesbar, bis ein Merge ihre noch gültigen Werte in neue Dateien übernimmt.",
            "An immutable data file is closed and no longer changed. It remains readable until merge copies its still-live values into new files.",
        ),
        "Put Operation": multilingual(
            "Put speichert einen neuen Wert unter einem Schlüssel oder legt eine neue Version für einen vorhandenen Schlüssel an. In Bitcask wird der Eintrag angehängt und die Keydir aktualisiert.",
            "Put stores a value under a key or creates a new version for an existing key. Bitcask appends the record and updates keydir.",
        ),
        "Get Operation": multilingual(
            "Get liest den aktuell gültigen Wert eines Schlüssels. Bitcask findet über die Keydir direkt Datei und Position, statt alle Dateien zu durchsuchen.",
            "Get reads the current value of a key. Bitcask uses keydir to locate the exact file and position instead of scanning every file.",
        ),
        "Delete Operation": multilingual(
            "Delete markiert einen Schlüssel als gelöscht. In append-only Speichern geschieht das zunächst mit einem Tombstone; der alte Wert verschwindet physisch erst beim späteren Aufräumen.",
            "Delete marks a key as deleted. In append-only storage, a tombstone is written first, and the old value disappears physically only during later cleanup.",
        ),
        "Merge Process": multilingual(
            "Der Bitcask-Merge liest geschlossene Dateien und schreibt nur die neuesten noch gültigen Werte in neue saubere Dateien. Alte Versionen und Löschmarker können dabei verschwinden.",
            "Bitcask merge reads closed files and writes only the newest live values into clean new files, removing obsolete versions and deletion markers when safe.",
        ),
        "Mutable Memtable": multilingual(
            "Die Mutable Memtable ist die aktuell beschreibbare sortierte Tabelle im Arbeitsspeicher. Neue LSM-Writes landen zuerst dort und parallel im Sicherheitslog.",
            "The mutable memtable is the currently writable sorted table in memory. New LSM writes enter it first and are also recorded in the safety log.",
        ),
        "Immutable Memtable": multilingual(
            "Wenn die Mutable Memtable voll ist, wird sie eingefroren. Als Immutable Memtable nimmt sie keine neuen Writes mehr an und wartet darauf, als SSTable auf Disk geschrieben zu werden.",
            "When the mutable memtable becomes full, it is frozen. As an immutable memtable, it accepts no new writes and waits to be written as an SSTable.",
        ),
        "Level-0": multilingual(
            "Level 0 enthält die frisch geflushten SSTables. Ihre Schlüsselbereiche dürfen sich überlappen, weshalb ein Read möglicherweise mehrere Level-0-Dateien prüfen muss.",
            "Level 0 contains freshly flushed SSTables. Their key ranges may overlap, so a read may need to inspect several level-0 files.",
        ),
        "Sparse Index": multilingual(
            "Ein Sparse Index speichert nicht jeden Schlüssel, sondern nur Wegweiser zu Datenblöcken. Er findet den passenden Block; innerhalb dieses Blocks wird weitergesucht.",
            "A sparse index stores signposts to data blocks rather than every key. It identifies the candidate block, which is then searched.",
        ),
        "False Positive": multilingual(
            "Ein False Positive bedeutet: Der Test sagt „wahrscheinlich vorhanden“, obwohl das Element fehlt. Beim Bloom-Filter kostet das nur einen unnötigen Dateizugriff.",
            "A false positive means the test says “probably present” even though the element is absent. For a Bloom filter, this causes an unnecessary file lookup.",
        ),
        "False Negative": multilingual(
            "Ein False Negative bedeutet: Der Test sagt „nicht vorhanden“, obwohl das Element existiert. Ein korrekter Bloom-Filter darf diesen Fehler nicht haben.",
            "A false negative means the test says “absent” even though the element exists. A correct Bloom filter must never produce this error.",
        ),
        "Range Query": multilingual(
            "Eine Range Query liest alle Schlüssel in einem Bereich, etwa von 1000 bis 1999. Sortierte Strukturen wie SSTables eignen sich dafür besser als eine reine Hash-Tabelle.",
            "A range query reads all keys within an interval, such as 1000 through 1999. Sorted structures such as SSTables support this better than a plain hash table.",
        ),
        "Space Amplification": multilingual(
            "Space Amplification beschreibt zusätzlichen Speicherverbrauch. Obwohl logisch nur eine aktuelle Version lebt, können alte Versionen, Tombstones und temporäre Compaction-Dateien noch Platz belegen.",
            "Space amplification is extra storage usage. Even when one logical version is live, obsolete versions, tombstones, and temporary compaction files may consume space.",
        ),
    }
)

BEGINNER_EXPLANATIONS.update(
    {
        "Arbiter": multilingual(
            "Ein MongoDB-Arbiter besitzt keine Nutzdaten. Er stimmt nur bei der Wahl eines Primary mit und hilft dadurch, eine Mehrheit zu erreichen.",
            "A MongoDB arbiter stores no user data. It only votes in primary elections and helps form a majority.",
        ),
        "BSON": multilingual(
            "BSON ist MongoDBs binäre Speicherform für JSON-ähnliche Dokumente. Es unterstützt zusätzliche Datentypen und wird intern effizient verarbeitet.",
            "BSON is MongoDB's binary representation of JSON-like documents. It supports additional data types and efficient internal processing.",
        ),
        "Document Store": multilingual(
            "Ein Document Store speichert zusammengehörige Daten als Dokumente, ähnlich JSON-Objekten. Die Datenbank kennt deren Felder und kann beispielsweise nach price oder address.city suchen.",
            "A document store keeps related data as JSON-like documents. The database understands their fields and can query price or address.city.",
        ),
        "mongos": multilingual(
            "mongos ist der Verteiler vor einem MongoDB-Sharded-Cluster. Clients schicken ihre Anfrage an mongos, und dieser leitet sie an die zuständigen Shards weiter.",
            "mongos is the router in front of a MongoDB sharded cluster. Clients send requests to mongos, which forwards them to the responsible shards.",
        ),
        "Replica Set": multilingual(
            "Ein Replica Set ist eine Gruppe von MongoDB-Servern mit denselben Daten. Einer ist Primary für Writes, die Secondaries übernehmen seine Änderungen und können bei Ausfall einen neuen Primary wählen.",
            "A replica set is a group of MongoDB servers holding the same data. One primary accepts writes, secondaries replicate them, and a new primary can be elected after failure.",
        ),
        "Shard Key": multilingual(
            "Der Shard Key entscheidet, auf welchem Shard ein MongoDB-Dokument liegt. Eine gute Wahl verteilt Last gleichmäßig und erlaubt wichtige Abfragen gezielt zu routen.",
            "The shard key decides which shard stores a MongoDB document. A good choice distributes load evenly and enables targeted routing of important queries.",
        ),
        "JSON": multilingual(
            "JSON ist eine lesbare Textschreibweise für verschachtelte Daten aus Objekten, Listen, Texten, Zahlen und Wahrheitswerten.",
            "JSON is a human-readable text format for nested data made of objects, arrays, strings, numbers, and Boolean values.",
        ),
        "BSON Document Limit": multilingual(
            "Ein einzelnes MongoDB-Dokument darf höchstens 16 MB groß sein. Unbegrenzt wachsende Arrays oder eingebettete Daten müssen deshalb oft ausgelagert werden.",
            "One MongoDB document may be at most 16 MB. Unbounded arrays or embedded data therefore often need to be stored separately.",
        ),
        "Reference": multilingual(
            "Eine Reference speichert nicht das andere Objekt selbst, sondern nur dessen ID. Die Anwendung lädt das referenzierte Dokument bei Bedarf separat.",
            "A reference stores only another object's ID rather than the object itself. The application loads the referenced document separately when needed.",
        ),
        "Array of References": multilingual(
            "Ein Array of References ist eine Liste von IDs zu mehreren anderen Dokumenten. Es bildet Beziehungen ab, ohne die vollständigen Objekte einzubetten.",
            "An array of references is a list of IDs pointing to several other documents. It represents relationships without embedding the full objects.",
        ),
        "One-to-Few": multilingual(
            "One-to-Few bedeutet: Ein Objekt besitzt nur wenige abhängige Objekte, etwa eine Person mit zwei Adressen. Diese wenigen Daten passen häufig direkt als eingebettetes Array ins Hauptdokument.",
            "One-to-few means one object has only a few dependents, such as a person with two addresses. They often fit directly into the main document.",
        ),
        "One-to-Thousands": multilingual(
            "Bei One-to-Thousands gibt es zu einem Objekt viele abhängige Objekte. Häufig speichert die One-Seite nur eine noch handhabbare Liste ihrer IDs statt alle Daten einzubetten.",
            "In one-to-thousands, one object has many dependents. The one side often stores a still-manageable list of their IDs instead of embedding all data.",
        ),
        "One-to-Millions": multilingual(
            "Bei One-to-Millions wären Einbettung oder eine riesige ID-Liste unpraktisch. Die vielen Objekte liegen deshalb separat und speichern meist selbst die ID des übergeordneten Objekts.",
            "In one-to-millions, embedding or one huge ID list is impractical. The many objects are stored separately and usually reference the parent.",
        ),
        "Primary": multilingual(
            "Der Primary ist im MongoDB Replica Set der Server, der Writes annimmt. Er protokolliert Änderungen, damit die Secondaries sie nachspielen können.",
            "The primary is the MongoDB replica-set member that accepts writes. It logs changes so secondaries can replay them.",
        ),
        "Secondary": multilingual(
            "Ein Secondary hält eine Kopie der MongoDB-Daten und übernimmt die Änderungen des Primary. Er kann Reads bedienen, dabei aber etwas hinter dem Primary zurückliegen.",
            "A secondary keeps a copy of MongoDB data and replays primary changes. It may serve reads but can lag behind the primary.",
        ),
        "Config Server": multilingual(
            "Config Server speichern die Landkarte eines MongoDB-Sharded-Clusters: welche Datenbereiche auf welchen Shards liegen und wie der Cluster aufgebaut ist.",
            "Config servers store the map of a MongoDB sharded cluster: which data ranges live on which shards and how the cluster is configured.",
        ),
        "Document Validation": multilingual(
            "Document Validation prüft beim Schreiben, ob ein MongoDB-Dokument festgelegte Regeln erfüllt, etwa ob age eine Zahl und email vorhanden ist.",
            "Document validation checks on write whether a MongoDB document follows defined rules, such as age being numeric and email being present.",
        ),
        "JSON Schema": multilingual(
            "Ein JSON Schema beschreibt, welche Felder ein JSON-Dokument haben darf oder muss und welche Datentypen dort erlaubt sind.",
            "A JSON Schema describes which fields a JSON document may or must contain and which data types are allowed.",
        ),
    }
)

BEGINNER_EXPLANATIONS.update(
    {
        "allShortestPaths": multilingual(
            "allShortestPaths sucht nicht nur irgendeinen kürzesten Weg, sondern alle Wege, die gemeinsam die kleinste mögliche Länge haben.",
            "allShortestPaths returns every path that shares the minimum possible length, not just one shortest path.",
        ),
        "Cypher": multilingual(
            "Cypher ist die Abfragesprache von Neo4j. Man beschreibt darin ein Muster aus Knoten und Beziehungen, und die Datenbank sucht passende Stellen im Graphen.",
            "Cypher is Neo4j's query language. You describe a pattern of nodes and relationships, and the database finds matching parts of the graph.",
        ),
        "DETACH DELETE": multilingual(
            "DETACH DELETE löscht einen Graphknoten und räumt gleichzeitig alle Beziehungen auf, die zu diesem Knoten führen oder von ihm ausgehen.",
            "DETACH DELETE removes a graph node together with every relationship entering or leaving it.",
        ),
        "Label": multilingual(
            "Ein Label ist eine Klassenbezeichnung für einen Knoten, etwa Person, City oder Airport. Ein Knoten kann mehrere Labels besitzen.",
            "A label classifies a node, such as Person, City, or Airport. One node may have several labels.",
        ),
        "Node Key": multilingual(
            "Ein Node Key verlangt für Knoten eines Labels bestimmte Properties und macht deren Kombination eindeutig. Er verbindet also Pflichtfelder mit Eindeutigkeit.",
            "A node key requires certain properties for nodes of a label and makes their combination unique, combining existence with uniqueness.",
        ),
        "Property Graph": multilingual(
            "Ein Property Graph besteht aus Dingen als Knoten, Verbindungen als gerichteten Beziehungen und zusätzlichen Eigenschaften auf beiden, etwa name am Knoten oder since an einer Beziehung.",
            "A property graph contains things as nodes, directed connections as relationships, and additional properties on both, such as name or since.",
        ),
        "shortestPath": multilingual(
            "shortestPath sucht einen Weg mit möglichst wenigen Beziehungen zwischen zwei Knoten. Gibt es mehrere gleich kurze Wege, wird nicht automatisch jeder davon geliefert.",
            "shortestPath finds a route with the fewest relationships between two nodes. If several are equally short, it does not automatically return all of them.",
        ),
        "Node": multilingual(
            "Ein Node ist ein einzelnes Objekt im Graphen, etwa eine Person, ein Flughafen oder ein Produkt.",
            "A node is one object in a graph, such as a person, airport, or product.",
        ),
        "Relationship": multilingual(
            "Eine Relationship ist eine gespeicherte Verbindung zwischen zwei Knoten, etwa Person WORKS_AT Company. Sie besitzt eine Richtung und kann eigene Daten tragen.",
            "A relationship is a stored connection between two nodes, such as Person WORKS_AT Company. It has a direction and may carry its own data.",
        ),
        "Relationship Type": multilingual(
            "Der Relationship Type benennt die Bedeutung einer Verbindung, zum Beispiel FRIEND_OF, BOUGHT oder FLIGHT. Er ist nicht dasselbe wie ihre Richtung.",
            "A relationship type names the meaning of a connection, such as FRIEND_OF, BOUGHT, or FLIGHT. It is separate from direction.",
        ),
        "Property": multilingual(
            "Eine Property ist ein benannter Wert an einem Knoten oder einer Beziehung, etwa name: 'Alice' oder distance: 250.",
            "A property is a named value on a node or relationship, such as name: 'Alice' or distance: 250.",
        ),
        "Path": multilingual(
            "Ein Path ist ein Weg durch den Graphen: eine abwechselnde Folge von Knoten und den Beziehungen zwischen ihnen.",
            "A path is a route through a graph: an alternating sequence of nodes and the relationships connecting them.",
        ),
        "MATCH": multilingual(
            "MATCH beschreibt das Graphmuster, das Cypher suchen soll. Es verändert keine Daten, sondern bindet passende Knoten und Beziehungen an Variablen.",
            "MATCH describes the graph pattern Cypher should find. It does not change data; it binds matching nodes and relationships to variables.",
        ),
        "WHERE": multilingual(
            "WHERE ist eine Subklausel von MATCH, OPTIONAL MATCH oder WITH. Bei MATCH schränkt es das zugehörige Pattern ein; nach WITH filtert es die weitergegebenen Zeilen.",
            "WHERE is a subclause of MATCH, OPTIONAL MATCH, or WITH. With MATCH it constrains the associated pattern; after WITH it filters the passed rows.",
        ),
        "RETURN": multilingual(
            "RETURN legt fest, was eine Cypher-Query ausgibt, etwa Namen, ganze Knoten, berechnete Werte oder Aggregate.",
            "RETURN selects what a Cypher query outputs, such as names, complete nodes, calculated values, or aggregates.",
        ),
        "DISTINCT": multilingual(
            "DISTINCT entfernt doppelte Ergebniszeilen. Derselbe Wert erscheint danach nur einmal, auch wenn mehrere Matches ihn erzeugt haben.",
            "DISTINCT removes duplicate result rows. A value appears only once even when several matches produced it.",
        ),
        "collect": multilingual(
            "collect sammelt mehrere Cypher-Ergebniswerte in einer Liste, etwa alle Flughafencodes einer Stadt.",
            "collect gathers several Cypher result values into one list, such as all airport codes of a city.",
        ),
        "count(*)": multilingual(
            "count(*) zählt die Ergebniszeilen einer Cypher-Gruppe. Anders als count(property) zählt es auch Zeilen, in denen eine bestimmte Property fehlt.",
            "count(*) counts result rows in a Cypher group. Unlike count(property), it also counts rows where that property is missing.",
        ),
        "Uniqueness Constraint": multilingual(
            "Ein Uniqueness Constraint verbietet doppelte Werte für eine bestimmte Property eines Labels, etwa zwei Person-Knoten mit derselben eindeutigen ID.",
            "A uniqueness constraint forbids duplicate values for a property of a label, such as two Person nodes sharing one unique ID.",
        ),
        "Existence Constraint": multilingual(
            "Ein Existence Constraint verlangt, dass eine bestimmte Property vorhanden ist, etwa dass jeder Airport einen code besitzt. Eindeutigkeit fordert er nicht.",
            "An existence constraint requires a property to be present, such as every Airport having a code. It does not require uniqueness.",
        ),
        "Bookmark": multilingual(
            "Ein Neo4j-Bookmark merkt sich, bis zu welcher bestätigten Transaktion ein Client gekommen ist. Ein späterer Read kann warten, bis er mindestens diesen Stand sehen kann.",
            "A Neo4j bookmark records the latest confirmed transaction seen by a client. A later read can wait until it can observe at least that state.",
        ),
    }
)

BEGINNER_EXPLANATIONS.update(
    {
        "Bit-Vector Encoding": multilingual(
            "Für jeden möglichen Wert wird eine Folge aus Nullen und Einsen gespeichert. Eine Eins an Position 5 bedeutet, dass Zeile 5 genau diesen Wert besitzt.",
            "One sequence of zeros and ones is stored for every possible value. A one at position 5 means row 5 has that value.",
        ),
        "Column Family": multilingual(
            "Eine Column Family ist eine vorab definierte Obergruppe verwandter Spalten in Bigtable, etwa contact. Darunter können flexible Qualifier wie email oder phone entstehen.",
            "A column family is a predefined group of related Bigtable columns, such as contact. Flexible qualifiers such as email or phone live inside it.",
        ),
        "Null Suppression": multilingual(
            "Wenn eine Spalte fast überall NULL enthält, speichert Null Suppression nur die wenigen vorhandenen Werte zusammen mit ihren Positionen.",
            "When a column is mostly NULL, null suppression stores only the few existing values together with their positions.",
        ),
        "Tablet": multilingual(
            "Ein Tablet ist ein zusammenhängender Bereich von Bigtable-Zeilen. Es ist das Paket, das auf Server verteilt und bei Lastverschiebungen verschoben wird.",
            "A tablet is a consecutive range of Bigtable rows. It is the unit distributed to servers and moved for load balancing.",
        ),
        "Row Store": multilingual(
            "Ein Row Store speichert alle Werte einer Zeile nebeneinander, etwa ID, Name und Preis eines Produkts. Das ist praktisch, wenn meist vollständige einzelne Datensätze gelesen werden.",
            "A row store keeps all values of one row together, such as a product's ID, name, and price. This fits workloads reading complete individual records.",
        ),
        "Vertical Fragmentation": multilingual(
            "Eine Tabelle wird physisch in ihre Spalten zerlegt. Damit die Werte später wieder zu richtigen Zeilen zusammengesetzt werden, müssen gemeinsame IDs oder Positionen erhalten bleiben.",
            "A table is physically split into its columns. Shared IDs or positions must remain so values can later be reconstructed into correct rows.",
        ),
        "Explicit ID": multilingual(
            "Bei einer Explicit ID steht neben jedem Spaltenwert die ID seiner ursprünglichen Zeile. Das erleichtert die Zuordnung, benötigt aber zusätzlichen Speicher.",
            "With an explicit ID, every column value stores the ID of its original row. This simplifies matching but requires extra space.",
        ),
        "Compression": multilingual(
            "Kompression stellt dieselben Daten platzsparender dar, etwa indem Wiederholungen zusammengefasst oder lange Texte durch kurze Nummern ersetzt werden.",
            "Compression represents the same data using less space, for example by grouping repetitions or replacing long strings with short numbers.",
        ),
        "Bitmap Index": multilingual(
            "Ein Bitmap Index speichert für jeden möglichen Wert einen Bitvektor. Gesetzte Bits zeigen direkt, in welchen Zeilen dieser Wert vorkommt.",
            "A bitmap index stores one bit vector per possible value. Set bits directly identify the rows containing that value.",
        ),
        "Position List": multilingual(
            "Eine Position List ist eine Liste der Zeilennummern, die einen Filter überlebt haben. Erst später werden für genau diese Positionen weitere Spaltenwerte geladen.",
            "A position list contains the row positions that survived a filter. Other column values are fetched later only for those positions.",
        ),
        "Read Store": multilingual(
            "Der Read Store ist der große, stark komprimierte und für Analysen optimierte Datenbereich. Einzelne Änderungen sind dort vergleichsweise teuer.",
            "The read store is the large, compressed data area optimized for analytics. Individual updates are comparatively expensive there.",
        ),
        "Write Store": multilingual(
            "Der Write Store ist ein kleinerer Bereich, der neue Änderungen schnell aufnehmen kann. Abfragen lesen Read und Write Store gemeinsam; später werden Änderungen zusammengeführt.",
            "The write store is a smaller area that accepts new changes quickly. Queries read both stores, and changes are merged later.",
        ),
        "Row Key": multilingual(
            "Der Row Key ist der Hauptschlüssel einer Bigtable-Zeile. Er bestimmt zugleich die Sortierreihenfolge und damit, welche Zeilen räumlich nahe beieinander liegen.",
            "The row key is the main key of a Bigtable row. It also determines sort order and therefore which rows are stored near each other.",
        ),
        "Column Qualifier": multilingual(
            "Ein Column Qualifier ist der flexible Name einer einzelnen Spalte innerhalb einer festen Column Family, etwa email in contact:email.",
            "A column qualifier is the flexible name of one column within a fixed column family, such as email in contact:email.",
        ),
        "Timestamp": multilingual(
            "Der Timestamp unterscheidet mehrere Versionen derselben Bigtable-Zelle. Ein Read kann dadurch den neuesten Wert oder gezielt ältere Werte anfordern.",
            "The timestamp distinguishes several versions of the same Bigtable cell. A read can request the newest value or selected older versions.",
        ),
        "Chubby": multilingual(
            "Chubby ist ein verteilter Koordinations- und Sperrdienst von Google. Bigtable nutzt ihn unter anderem, damit Server sich über Zuständigkeiten und wichtige Metadaten einigen.",
            "Chubby is Google's distributed coordination and lock service. Bigtable uses it to agree on responsibilities and important metadata.",
        ),
    }
)

EXAM_TAKEAWAYS = {
    "ACID": multilingual(
        "ACID = Atomicity, Consistency, Isolation, Durability: ganz oder gar nicht, gültiger Zustand, kontrollierte Parallelität, nach Commit dauerhaft.",
        "ACID = atomicity, consistency, isolation, durability: all or nothing, valid state, controlled concurrency, durable after commit.",
    ),
    "CAP-Theorem": multilingual(
        "Bei einer Partition ist vollständige Consistency und vollständige Availability nicht gleichzeitig garantierbar; praktisch entscheidet man zwischen CP und AP.",
        "During a partition, full consistency and full availability cannot both be guaranteed; the practical choice is CP versus AP.",
    ),
    "PACELC": multilingual(
        "P: A vs. C; Else: Latency vs. Consistency.",
        "P: A versus C; Else: latency versus consistency.",
    ),
    "Quorum Consensus": multilingual(
        "Immer beide Bedingungen prüfen: 2W > N und R + W > N.",
        "Always check both conditions: 2W > N and R + W > N.",
    ),
    "Lamport Clock": multilingual(
        "Receive: max(lokal, empfangen) + 1; aus kleinerem Zeitstempel folgt nicht automatisch Kausalität.",
        "Receive: max(local, received) + 1; a smaller timestamp does not automatically imply causality.",
    ),
    "Vector Clock": multilingual(
        "Komponentenweise vergleichen: ≤ in allen und < in mindestens einer Komponente bedeutet kausal kleiner; kreuzende Werte bedeuten nebenläufig.",
        "Compare component-wise: ≤ everywhere and < somewhere means causally smaller; crossed components mean concurrent.",
    ),
    "Flush": multilingual(
        "Flush: Immutable Memtable → neue SSTable auf Level 0; keine allgemeine Dateibereinigung.",
        "Flush: immutable memtable → new level-0 SSTable; it is not general file cleanup.",
    ),
    "Compaction": multilingual(
        "Compaction reorganisiert SSTables und entfernt alte Versionen/Tombstones; sie erhöht typischerweise Write Amplification.",
        "Compaction reorganizes SSTables and removes obsolete versions/tombstones; it typically increases write amplification.",
    ),
    "LSM-Tree": multilingual(
        "Write-Pfad: WAL + Mutable Memtable → Immutable Memtable → Flush zu SSTable → spätere Compaction.",
        "Write path: WAL + mutable memtable → immutable memtable → flush to SSTable → later compaction.",
    ),
    "Bloom Filter": multilingual(
        "Keine False Negatives; ein positives Ergebnis kann ein False Positive sein.",
        "No false negatives; a positive result may be a false positive.",
    ),
    "Read Concern": multilingual(
        "Read Preference = wo lesen; Read Concern = welchen bestätigten Datenstand lesen.",
        "Read preference = where to read; read concern = which confirmed view may be read.",
    ),
    "Read Preference": multilingual(
        "Read Preference bestimmt das Read-Ziel, nicht die Konsistenzgarantie.",
        "Read preference selects the read target, not the consistency guarantee.",
    ),
    "Write Concern": multilingual(
        "Write Concern bestimmt, wann ein Write als ausreichend bestätigt gilt.",
        "Write concern determines when a write is sufficiently acknowledged.",
    ),
    "MERGE": multilingual(
        "MERGE matcht das vollständige angegebene Pattern; zusätzliche Properties können deshalb unerwartete Duplikate erzeugen.",
        "MERGE matches the complete specified pattern; extra properties can therefore create unexpected duplicates.",
    ),
    "Variable-Length Path": multilingual(
        "*2 = genau zwei Beziehungen; *1..2 = eine oder zwei; *0..1 erlaubt auch den Startknoten.",
        "*2 = exactly two relationships; *1..2 = one or two; *0..1 also allows the start node.",
    ),
    "shortestPath": multilingual(
        "shortestPath liefert einen kürzesten Pfad pro Match; allShortestPaths liefert alle gleich kurzen kürzesten Pfade.",
        "shortestPath returns one shortest path per match; allShortestPaths returns all equally short shortest paths.",
    ),
    "Late Materialization": multilingual(
        "Positionen möglichst lange weiterreichen und Werte erst nach Filtern/Joins mit reconstruct nachladen.",
        "Carry positions as long as possible and fetch values with reconstruct only after filters/joins.",
    ),
    "Run-Length Encoding": multilingual(
        "RLE lohnt sich bei langen Folgen gleicher Werte, nicht allgemein bei jeder Spalte.",
        "RLE is effective for long runs of equal values, not for every column.",
    ),
    "Wide Column Store": multilingual(
        "(Row Key, Family:Qualifier, Timestamp) → Value; Column Family und Qualifier nicht verwechseln.",
        "(row key, family:qualifier, timestamp) → value; do not confuse column family and qualifier.",
    ),
}


def search_tokens(*values: str) -> set[str]:
    text = " ".join(str(value) for value in values if value)
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.casefold())
        if len(token) > 1 and token not in SEARCH_STOPWORDS
    }


def section_text(section: dict[str, Any]) -> str:
    return " ".join(
        [
            section.get("title", ""),
            section.get("body", ""),
            *section.get("bullets", []),
            section.get("formula", ""),
            section.get("example", ""),
            section.get("pitfall", ""),
        ]
    )


def topic_view(topic: dict[str, Any], lang: str) -> dict[str, Any]:
    if lang == "en" and topic.get("translations", {}).get("en"):
        return {**topic, **topic["translations"]["en"]}
    return topic


def best_section(
    entry: dict[str, Any], topic: dict[str, Any], lang: str
) -> tuple[int, dict[str, Any]]:
    view = topic_view(topic, lang)
    sections = view.get("sections", [])
    if not sections:
        return 0, {}

    term = entry_text(entry, "term", lang)
    definition = entry_text(entry, "definition", lang)
    aliases = entry.get("aliases", [])
    needles = search_tokens(term, definition, *aliases, *entry.get("tags", []))
    term_folded = term.casefold()

    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, section in enumerate(sections):
        haystack = section_text(section)
        haystack_folded = haystack.casefold()
        overlap = len(needles.intersection(search_tokens(haystack)))
        score = overlap * 3
        if term_folded and term_folded in haystack_folded:
            score += 30
        for alias in aliases:
            if alias.casefold() in haystack_folded:
                score += 12
        scored.append((score, -index, section))

    score, negative_index, section = max(scored, key=lambda item: (item[0], item[1]))
    return -negative_index, section


def question_text(question: dict[str, Any]) -> str:
    values = [
        str(question.get("prompt", "")),
        str(question.get("context", "")),
        str(question.get("explanation", "")),
        " ".join(question.get("tags", [])),
    ]
    for option in question.get("options", []):
        values.extend([str(option.get("text", "")), str(option.get("explanation", ""))])
    return " ".join(values)


def related_questions(
    entry: dict[str, Any],
    section: dict[str, Any],
    questions: list[dict[str, Any]],
    limit: int = 2,
) -> list[dict[str, Any]]:
    candidates = [
        question
        for question in questions
        if question.get("topic") == entry["topic"]
        and question.get("status", "active") == "active"
    ]
    if not candidates:
        return []

    term = entry["term"].casefold()
    aliases = [alias.casefold() for alias in entry.get("aliases", [])]
    term_tokens = search_tokens(entry["term"], *entry.get("aliases", []))
    definition_tokens = search_tokens(entry["definition"])
    tag_tokens = search_tokens(*entry.get("tags", []))
    section_tokens = search_tokens(section.get("title", ""))
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for question in candidates:
        text = question_text(question)
        folded = text.casefold()
        text_tokens = search_tokens(text)
        term_overlap = term_tokens.intersection(text_tokens)
        definition_overlap = definition_tokens.intersection(text_tokens)
        question_tag_overlap = tag_tokens.intersection(
            search_tokens(*question.get("tags", []))
        )
        score = 6 * len(term_overlap)
        score += len(definition_overlap)
        score += 4 * len(question_tag_overlap)
        score += len(section_tokens.intersection(text_tokens))
        exact_match = term in folded
        alias_match = any(alias and alias in folded for alias in aliases)
        if exact_match:
            score += 30
        if alias_match:
            score += 12
        qualified = (
            exact_match
            or alias_match
            or (term_tokens and term_tokens.issubset(text_tokens))
        )
        if qualified:
            ranked.append((score, question["id"], question))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked][:limit]


def option_text(option: dict[str, Any], lang: str) -> str:
    value = option.get("text", "")
    if isinstance(value, dict):
        return value.get(lang) or value.get("de") or value.get("en") or ""
    return str(value)


def question_value(question: dict[str, Any], field: str, lang: str) -> str:
    value = question.get(field, "")
    if isinstance(value, dict):
        return value.get(lang) or value.get("de") or value.get("en") or ""
    return str(value)


def answer_for_question(question: dict[str, Any], lang: str) -> str:
    correct = [
        option_text(option, lang)
        for option in question.get("options", [])
        if option.get("correct")
    ]
    if lang == "de":
        selection = (
            "Korrekt sind: " + " · ".join(correct)
            if correct
            else "Keine der Aussagen ist korrekt."
        )
    else:
        selection = (
            "Correct statements: " + " · ".join(correct)
            if correct
            else "None of the statements is correct."
        )
    explanation = question_value(question, "explanation", lang)
    return f"{selection} {explanation}".strip()


def best_option(
    question: dict[str, Any],
    entry: dict[str, Any],
    correct: bool,
) -> dict[str, Any] | None:
    candidates = [
        option
        for option in question.get("options", [])
        if option.get("correct") is correct
    ]
    if not candidates:
        return None
    concept_tokens = search_tokens(
        entry["term"],
        entry["definition"],
        *entry.get("aliases", []),
    )
    return max(
        candidates,
        key=lambda option: len(
            concept_tokens.intersection(
                search_tokens(
                    option_text(option, "de"),
                    str(option.get("explanation", "")),
                )
            )
        ),
    )


def question_as_example(
    question: dict[str, Any], entry: dict[str, Any], lang: str
) -> str:
    context = question_value(question, "context", lang)
    selected = best_option(question, entry, True)
    correct = option_text(selected, lang) if selected else ""
    prompt = question_value(question, "prompt", lang)
    if context:
        return f"{context} Daraus folgt: {correct}" if lang == "de" else f"{context} Therefore: {correct}"
    return f"{prompt} Beispielaussage: {correct}" if lang == "de" else f"{prompt} Example statement: {correct}"


def question_as_pitfall(
    question: dict[str, Any], entry: dict[str, Any], lang: str
) -> str:
    wrong = best_option(question, entry, False)
    if not wrong:
        return ""
    false_claim = option_text(wrong, lang)
    explanation = wrong.get("explanation", "")
    if isinstance(explanation, dict):
        explanation = (
            explanation.get(lang) or explanation.get("de") or explanation.get("en") or ""
        )
    prefix = "Falsch wäre: " if lang == "de" else "A false claim would be: "
    return f"{prefix}{false_claim} — {explanation}"


def translated_section(
    entry: dict[str, Any], topic: dict[str, Any], lang: str
) -> tuple[int, dict[str, Any]]:
    return best_section(entry, topic, lang)


def relevant_section_bullets(
    entry: dict[str, Any],
    section: dict[str, Any],
    lang: str,
    limit: int = 3,
) -> list[str]:
    term = entry["term"] if lang == "de" else entry_text(entry, "term", "en")
    definition = (
        entry["definition"] if lang == "de" else entry_text(entry, "definition", "en")
    )
    needles = search_tokens(term, definition, *entry.get("tags", []))
    ranked = [
        (
            len(needles.intersection(search_tokens(bullet))),
            -index,
            bullet,
        )
        for index, bullet in enumerate(section.get("bullets", []))
    ]
    ranked.sort(reverse=True)
    return [bullet for _, _, bullet in ranked[:limit]]


def make_study_detail(
    entry: dict[str, Any],
    related: list[str],
    topic: dict[str, Any],
    questions: list[dict[str, Any]],
    glossary_by_term: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    section_index_de, section_de = translated_section(entry, topic, "de")
    section_index_en, section_en = translated_section(entry, topic, "en")
    matches = related_questions(entry, section_de, questions)
    definition_en = entry_text(entry, "definition", "en")
    term_en = entry_text(entry, "term", "en")

    def key_points(lang: str, section: dict[str, Any]) -> list[str]:
        definition = entry["definition"] if lang == "de" else definition_en
        simple = BEGINNER_EXPLANATIONS[entry["term"]][lang]
        takeaway = exam_takeaway(entry)[lang]
        bullets = relevant_section_bullets(entry, section, lang, 1)
        return unique_strings([simple, definition, takeaway, *bullets], 5)

    def details(lang: str, section: dict[str, Any]) -> list[str]:
        term = entry["term"] if lang == "de" else term_en
        definition = entry["definition"] if lang == "de" else definition_en
        simple = BEGINNER_EXPLANATIONS[entry["term"]][lang]
        body = section.get("body", "")
        section_title = section.get("title", "")
        bullets = relevant_section_bullets(entry, section, lang)
        if lang == "de":
            values = [
                f"Grundidee: {simple}",
                f"Fachliche Definition: {definition}",
                f"Einordnung in das Kapitel „{section_title}“: {body}",
                *[f"Wichtiger Zusammenhang: {bullet}" for bullet in bullets],
            ]
        else:
            values = [
                f"Core idea: {simple}",
                f"Technical definition: {definition}",
                f"Context in the chapter “{section_title}”: {body}",
                *[f"Important connection: {bullet}" for bullet in bullets],
            ]
        return unique_strings([value for value in values if value], 8)

    def examples(lang: str, section: dict[str, Any]) -> list[str]:
        curated = CONCRETE_EXAMPLES.get(entry["term"], {}).get(lang, "")
        beginner = BEGINNER_EXPLANATIONS[entry["term"]][lang]
        beginner_example = (
            f"Einfaches Anwendungsbild für „{entry['term']}“: {beginner}"
            if lang == "de"
            else f"Simple application picture for “{term_en}”: {beginner}"
        )
        values = [curated or beginner_example, section.get("example", "")]
        values.extend(
            question_as_example(question, entry, lang) for question in matches[:1]
        )
        return unique_strings([value for value in values if value], 5)

    def pitfalls(lang: str, section: dict[str, Any]) -> list[str]:
        curated = CONCEPT_PITFALLS.get(entry["term"], {}).get(lang, "")
        entry_tokens = search_tokens(
            entry["term"],
            entry["definition"],
        )
        related_candidates = []
        for related_term in related:
            candidate = glossary_by_term.get(related_term)
            if not candidate:
                continue
            overlap = len(
                entry_tokens.intersection(
                    search_tokens(candidate["term"], candidate["definition"])
                )
            )
            if overlap:
                related_candidates.append((overlap, candidate))
        related_entry = (
            max(related_candidates, key=lambda item: item[0])[1]
            if related_candidates
            else None
        )
        distinction = ""
        if related_entry:
            related_term = (
                related_entry["term"]
                if lang == "de"
                else entry_text(related_entry, "term", "en")
            )
            related_definition = (
                related_entry["definition"]
                if lang == "de"
                else entry_text(related_entry, "definition", "en")
            )
            if lang == "de":
                distinction = (
                    f"Abgrenzung zu „{related_term}“: „{entry['term']}“ bedeutet "
                    f"{entry['definition']} „{related_term}“ bezeichnet dagegen "
                    f"{related_definition}"
                )
            else:
                distinction = (
                    f"Distinction from “{related_term}”: “{term_en}” means "
                    f"{definition_en} “{related_term}” instead means "
                    f"{related_definition}"
                )
        values = [curated, distinction, section.get("pitfall", "")]
        values.extend(
            question_as_pitfall(question, entry, lang) for question in matches[:1]
        )
        return unique_strings([value for value in values if value], 5)

    exam_questions = [
        {
            "q": multilingual(
                question_value(question, "prompt", "de"),
                f"Explain {term_en} in the context of {section_en.get('title', topic_view(topic, 'en').get('title', entry['topic']))}.",
            ),
            "a": multilingual(
                answer_for_question(question, "de"),
                f"{definition_en} {section_en.get('body', '')}".strip(),
            ),
            "source": question.get("source", {}),
            "questionId": question["id"],
        }
        for question in matches
    ]
    if not exam_questions:
        example_de = CONCRETE_EXAMPLES.get(entry["term"], {}).get(
            "de", section_de.get("example", "")
        )
        example_en = CONCRETE_EXAMPLES.get(entry["term"], {}).get(
            "en", section_en.get("example", "")
        )
        exam_questions.append(
            {
                "q": multilingual(
                    (
                        f"Erkläre „{entry['term']}“ anhand dieses Beispiels: {example_de}"
                        if example_de
                        else f"Erkläre „{entry['term']}“ und ordne den Begriff in den Zusammenhang „{section_de.get('title', topic.get('title', entry['topic']))}“ ein."
                    ),
                    (
                        f"Explain “{term_en}” using this example: {example_en}"
                        if example_en
                        else f"Explain “{term_en}” and place it in the context of “{section_en.get('title', topic_view(topic, 'en').get('title', entry['topic']))}”."
                    ),
                ),
                "a": multilingual(
                    f"{entry['definition']} {section_de.get('body', '')}".strip(),
                    f"{definition_en} {section_en.get('body', '')}".strip(),
                ),
            }
        )

    return {
        "summary": multilingual(entry["definition"], definition_en),
        "keyPoints": {
            "de": key_points("de", section_de),
            "en": key_points("en", section_en),
        },
        "details": {
            "de": details("de", section_de),
            "en": details("en", section_en),
        },
        "examples": {
            "de": examples("de", section_de),
            "en": examples("en", section_en),
        },
        "watchOut": {
            "de": pitfalls("de", section_de),
            "en": pitfalls("en", section_en),
        },
        "examQuestions": exam_questions,
        "related": related,
        "sourceSection": multilingual(
            section_de.get("title", topic.get("title", entry["topic"])),
            section_en.get(
                "title", topic_view(topic, "en").get("title", entry["topic"])
            ),
        ),
        "sourceSectionIndex": {"de": section_index_de, "en": section_index_en},
        "sourceDeck": topic.get("deck", ""),
        "practiceQuestionIds": [question["id"] for question in matches],
    }


def unique_strings(values: list[str], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip().casefold()
        if value and normalized not in seen:
            result.append(value)
            seen.add(normalized)
        if len(result) >= limit:
            break
    return result


def merge_localized_lists(
    generated: Any, explicit: Any, limit: int
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for lang in ("de", "en"):
        generated_values = (
            generated.get(lang, []) if isinstance(generated, dict) else generated or []
        )
        explicit_values = (
            explicit.get(lang, []) if isinstance(explicit, dict) else explicit or []
        )
        result[lang] = unique_strings(
            [*explicit_values, *generated_values],
            limit,
        )
    return result


def merge_exam_questions(
    generated: list[dict[str, Any]], explicit: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*explicit, *generated]:
        question = item.get("q", {})
        key = (
            question.get("de", "")
            if isinstance(question, dict)
            else str(question)
        ).strip().casefold()
        if key and key not in seen:
            result.append(item)
            seen.add(key)
        if len(result) >= 3:
            break
    return result


def concise_example(values: list[str]) -> str:
    question_starts = (
        "welche ",
        "was ",
        "wie ",
        "warum ",
        "gegeben ",
        "ein system ",
        "prozess ",
        "which ",
        "what ",
        "how ",
        "why ",
        "given ",
        "a system ",
        "process ",
    )
    for value in values:
        normalized = " ".join(value.split()).strip()
        if not normalized or normalized.casefold().startswith(question_starts):
            continue
        first_sentence = re.split(r"(?<=[.!?])\s+", normalized, maxsplit=1)[0]
        if len(first_sentence) <= 300:
            return first_sentence
        shortened = first_sentence[:297].rsplit(" ", 1)[0]
        return f"{shortened} …"
    return ""


def beginner_explanation(
    entry: dict[str, Any],
    detail: dict[str, Any],
) -> dict[str, str]:
    explicit = BEGINNER_EXPLANATIONS.get(entry["term"])
    result: dict[str, str] = {}
    for lang in ("de", "en"):
        if explicit and explicit.get(lang):
            result[lang] = explicit[lang]
            continue
        term = entry["term"] if lang == "de" else entry_text(entry, "term", "en")
        definition = (
            entry["definition"] if lang == "de" else entry_text(entry, "definition", "en")
        )
        examples = detail.get("examples", {}).get(lang, [])
        example = concise_example(examples)
        if lang == "de":
            result[lang] = (
                f"{term} bedeutet vereinfacht: {definition} Ein konkretes Bild dazu: {example}"
                if example
                else f"{term} bedeutet vereinfacht: {definition}"
            )
        else:
            result[lang] = (
                f"In simple terms, {term} means: {definition} A concrete example is: {example}"
                if example
                else f"In simple terms, {term} means: {definition}"
            )
    return result


def exam_takeaway(entry: dict[str, Any]) -> dict[str, str]:
    explicit = EXAM_TAKEAWAYS.get(entry["term"])
    if explicit:
        return explicit
    return multilingual(
        f"{entry['term']}: {entry['definition']}",
        f"{entry_text(entry, 'term', 'en')}: {entry_text(entry, 'definition', 'en')}",
    )


def semantic_related_terms(
    entry: dict[str, Any],
    candidates: list[dict[str, Any]],
    topic: dict[str, Any],
    limit: int = 5,
) -> list[str]:
    entry_section_index, _ = best_section(entry, topic, "de")
    entry_tokens = search_tokens(
        entry["term"],
        entry["definition"],
        *default_tags(entry),
    )
    ranked: list[tuple[int, str]] = []
    for candidate in candidates:
        if candidate["term"] == entry["term"]:
            continue
        candidate_section_index, _ = best_section(candidate, topic, "de")
        candidate_tokens = search_tokens(
            candidate["term"],
            candidate["definition"],
            *default_tags(candidate),
        )
        score = 3 * len(entry_tokens.intersection(candidate_tokens))
        if candidate_section_index == entry_section_index:
            score += 12
        ranked.append((score, candidate["term"]))
    ranked.sort(key=lambda item: (-item[0], item[1].casefold()))
    return [term for _, term in ranked[:limit]]


def enrich_glossary(
    entries: list[dict[str, Any]],
    topics: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    details = read_optional_json(CONTENT_DIR / "glossary.details.json", {})
    topic_map = {topic["id"]: topic for topic in topics}
    glossary_by_term = {entry["term"]: entry for entry in entries}
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_topic.setdefault(entry["topic"], []).append(entry)

    enriched = []
    for entry in entries:
        item = dict(entry)
        tags = default_tags(item)
        explicit = details.get(item["term"], {})
        tags = sorted(set(tags).union(explicit.get("tags", [])))

        fallback_related = semantic_related_terms(
            item,
            by_topic[item["topic"]],
            topic_map[item["topic"]],
        )

        detail = make_study_detail(
            item,
            fallback_related,
            topic_map[item["topic"]],
            questions,
            glossary_by_term,
        )
        for key, value in explicit.items():
            if key == "tags":
                continue
            if key in {"keyPoints", "details", "examples", "watchOut"}:
                detail[key] = merge_localized_lists(detail.get(key), value, 12)
            elif key == "examQuestions":
                detail[key] = merge_exam_questions(
                    detail.get(key, []),
                    value,
                )
            else:
                detail[key] = value
        detail.setdefault("related", fallback_related)
        detail.setdefault("simpleExplanation", beginner_explanation(item, detail))
        detail.setdefault("examTakeaway", exam_takeaway(item))

        item["tags"] = tags
        item["detail"] = detail
        enriched.append(item)
    return enriched


def attach_study_links(
    topics: list[dict[str, Any]],
    glossary: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    glossary_by_term = {entry["term"]: entry for entry in glossary}
    glossary_by_topic: dict[str, list[dict[str, Any]]] = {}
    questions_by_topic: dict[str, list[dict[str, Any]]] = {}
    for entry in glossary:
        glossary_by_topic.setdefault(entry["topic"], []).append(entry)
    for question in questions:
        questions_by_topic.setdefault(question["topic"], []).append(question)

    for topic in topics:
        topic_glossary = glossary_by_topic.get(topic["id"], [])
        topic_questions = questions_by_topic.get(topic["id"], [])
        for index, section in enumerate(topic.get("sections", [])):
            section_tokens = search_tokens(section_text(section))
            assigned = [
                entry
                for entry in topic_glossary
                if entry.get("detail", {})
                .get("sourceSectionIndex", {})
                .get("de")
                == index
            ]
            ranked_terms = sorted(
                (
                    (
                        5
                        * len(
                            section_tokens.intersection(
                                search_tokens(
                                    entry["term"],
                                    entry["definition"],
                                    *entry.get("tags", []),
                                )
                            )
                        )
                        + (20 if entry in assigned else 0),
                        entry["term"],
                        entry,
                    )
                    for entry in topic_glossary
                ),
                key=lambda item: (-item[0], item[1].casefold()),
            )
            override_terms = SECTION_TERM_OVERRIDES.get((topic["id"], index), [])
            selected_terms = [
                glossary_by_term[term]
                for term in override_terms
                if term in glossary_by_term
            ]
            target_term_count = (
                len(selected_terms)
                if selected_terms
                else max(5, min(8, len(assigned)))
            )
            for _, _, entry in ranked_terms:
                if len(selected_terms) >= target_term_count:
                    break
                if entry not in selected_terms:
                    selected_terms.append(entry)
            section["studyTerms"] = [entry["term"] for entry in selected_terms]

            term_tokens = search_tokens(
                *[
                    value
                    for entry in selected_terms
                    for value in (entry["term"], entry["definition"])
                ]
            )
            ranked_questions = sorted(
                (
                    (
                        4
                        * len(section_tokens.intersection(search_tokens(question_text(question))))
                        + len(term_tokens.intersection(search_tokens(question_text(question))))
                        + (200 if not question.get("_generated") else 0),
                        question["id"],
                        question,
                    )
                    for question in topic_questions
                ),
                key=lambda item: (-item[0], item[1]),
            )
            section["questionIds"] = [
                question["id"] for _, _, question in ranked_questions[:5]
            ]
    return topics


def attach_topic_translations(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    english = {
        entry["id"]: entry
        for entry in read_optional_json(CONTENT_DIR / "topics.en.json", [])
    }
    localized = []
    for topic in topics:
        item = dict(topic)
        if topic["id"] in english:
            item.setdefault("translations", {})["en"] = english[topic["id"]]
        localized.append(item)
    return localized


def entry_text(entry: dict[str, Any], field: str, lang: str) -> str:
    if lang == "de":
        return entry[field]
    return entry.get("translations", {}).get("en", {}).get(field, entry[field])


def glossary_options(
    entries: list[dict[str, Any]], index: int, topic: str | None = None
) -> list[dict[str, Any]]:
    pool = [entry for entry in entries if topic is None or entry["topic"] == topic]
    if len(pool) < 4:
        pool = entries
    selected = []
    cursor = index
    while len(selected) < 4:
        candidate = pool[cursor % len(pool)]
        if candidate not in selected:
            selected.append(candidate)
        cursor += 7
    return selected


def learning_explanation(
    entry: dict[str, Any],
    lang: str,
    *,
    prefix_de: str = "",
    prefix_en: str = "",
) -> str:
    term = entry["term"] if lang == "de" else entry_text(entry, "term", "en")
    definition = (
        entry["definition"] if lang == "de" else entry_text(entry, "definition", "en")
    )
    simple = entry.get("detail", {}).get("simpleExplanation", {}).get(lang, "")
    prefix = prefix_de if lang == "de" else prefix_en
    core = (
        f"„{term}“ bedeutet: {definition}"
        if lang == "de"
        else f"“{term}” means: {definition}"
    )
    return " ".join(part for part in (prefix, core, simple) if part).strip()


def generate_glossary_questions(glossary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for entry in glossary:
        by_topic.setdefault(entry["topic"], []).append(entry)

    for index, entry in enumerate(glossary):
        options = glossary_options(glossary, index + 1, entry["topic"])
        if entry not in options:
            options[-1] = entry
        questions.append(
            {
                "id": f"glossary-def-{index + 1:03d}",
                "topic": entry["topic"],
                "difficulty": 1 + (index % 2),
                "status": "active",
                "prompt": multilingual(
                    f"Welche Definition beschreibt den Begriff „{entry['term']}“ korrekt?",
                    f"Which definition correctly describes the term “{entry_text(entry, 'term', 'en')}”?",
                ),
                "options": [
                    {
                        "id": chr(97 + option_index),
                        "text": multilingual(
                            candidate["definition"],
                            entry_text(candidate, "definition", "en"),
                        ),
                        "correct": candidate is entry,
                        "explanation": multilingual(
                            learning_explanation(
                                candidate,
                                "de",
                                prefix_de=(
                                    "Die Definition passt."
                                    if candidate is entry
                                    else f"Die Definition gehört nicht zu „{entry['term']}“."
                                ),
                            ),
                            learning_explanation(
                                candidate,
                                "en",
                                prefix_en=(
                                    "The definition matches."
                                    if candidate is entry
                                    else f"The definition does not describe “{entry_text(entry, 'term', 'en')}”."
                                ),
                            ),
                        ),
                    }
                    for option_index, candidate in enumerate(options)
                ],
                "explanation": multilingual(
                    learning_explanation(entry, "de"),
                    learning_explanation(entry, "en"),
                ),
                "source": {"deck": "Glossar", "pages": "Definition drill"},
                "tags": ["Glossar", "Definition"],
                "_generated": True,
                "_languages": ["de", "en"],
            }
        )

        term_options = glossary_options(glossary, index + 3, entry["topic"])
        if entry not in term_options:
            term_options[0] = entry
        questions.append(
            {
                "id": f"glossary-term-{index + 1:03d}",
                "topic": entry["topic"],
                "difficulty": 2,
                "status": "active",
                "prompt": multilingual(
                    "Welcher Begriff passt zu dieser Definition?",
                    "Which term matches this definition?",
                ),
                "context": multilingual(
                    entry["definition"],
                    entry_text(entry, "definition", "en"),
                ),
                "options": [
                    {
                        "id": chr(97 + option_index),
                        "text": multilingual(
                            candidate["term"],
                            entry_text(candidate, "term", "en"),
                        ),
                        "correct": candidate is entry,
                        "explanation": multilingual(
                            learning_explanation(
                                candidate,
                                "de",
                                prefix_de=(
                                    "Das ist der gesuchte Begriff."
                                    if candidate is entry
                                    else f"Das ist nicht der gesuchte Begriff „{entry['term']}“."
                                ),
                            ),
                            learning_explanation(
                                candidate,
                                "en",
                                prefix_en=(
                                    "This is the requested term."
                                    if candidate is entry
                                    else f"This is not the requested term “{entry_text(entry, 'term', 'en')}”."
                                ),
                            ),
                        ),
                    }
                    for option_index, candidate in enumerate(term_options)
                ],
                "explanation": multilingual(
                    learning_explanation(
                        entry,
                        "de",
                        prefix_de=f"Gesucht ist „{entry['term']}“.",
                    ),
                    learning_explanation(
                        entry,
                        "en",
                        prefix_en=f"The requested term is “{entry_text(entry, 'term', 'en')}”.",
                    ),
                ),
                "source": {"deck": "Glossar", "pages": "Reverse drill"},
                "tags": ["Glossar", "Begriff"],
                "_generated": True,
                "_languages": ["de", "en"],
            }
        )

    pair_quotas = {"nosql": 9, "key-value": 8, "document": 8, "graph": 8, "column": 8}
    pair_index = 1
    for topic, quota in pair_quotas.items():
        pool = by_topic[topic]
        for offset, entry in enumerate(pool[:quota]):
            correct_other = pool[(offset + 2) % len(pool)]
            wrong_a = pool[(offset + 3) % len(pool)]
            wrong_b = pool[(offset + 5) % len(pool)]
            candidates = [
                (entry, entry, True),
                (correct_other, correct_other, True),
                (wrong_a, pool[(offset + 4) % len(pool)], False),
                (wrong_b, pool[(offset + 6) % len(pool)], False),
            ]
            questions.append(
                {
                    "id": f"glossary-pair-{pair_index:03d}",
                    "topic": topic,
                    "difficulty": 3 + (offset % 3),
                    "status": "active",
                    "prompt": multilingual(
                        "Welche Begriff-Definition-Paare sind korrekt?",
                        "Which term-definition pairs are correct?",
                    ),
                    "options": [
                        {
                            "id": chr(97 + option_index),
                            "text": multilingual(
                                f"{term_entry['term']} — {definition_entry['definition']}",
                                f"{entry_text(term_entry, 'term', 'en')} — {entry_text(definition_entry, 'definition', 'en')}",
                            ),
                            "correct": is_correct,
                            "explanation": multilingual(
                                (
                                    learning_explanation(
                                        term_entry,
                                        "de",
                                        prefix_de="Begriff und Definition gehören zusammen.",
                                    )
                                    if is_correct
                                    else " ".join(
                                        [
                                            f"Die angegebene Definition gehört zu „{definition_entry['term']}“, nicht zu „{term_entry['term']}“.",
                                            learning_explanation(term_entry, "de"),
                                            learning_explanation(definition_entry, "de"),
                                        ]
                                    )
                                ),
                                (
                                    learning_explanation(
                                        term_entry,
                                        "en",
                                        prefix_en="Term and definition match.",
                                    )
                                    if is_correct
                                    else " ".join(
                                        [
                                            f"The given definition belongs to “{entry_text(definition_entry, 'term', 'en')}”, not to “{entry_text(term_entry, 'term', 'en')}”.",
                                            learning_explanation(term_entry, "en"),
                                            learning_explanation(definition_entry, "en"),
                                        ]
                                    )
                                ),
                            ),
                        }
                        for option_index, (term_entry, definition_entry, is_correct) in enumerate(candidates)
                    ],
                    "explanation": multilingual(
                        "Prüfe jedes Paar über die konkrete Bedeutung des Begriffs. Die Erklärungen unter den Optionen ordnen beide vertauschten Begriffe vollständig zu.",
                        "Check each pair against the concrete meaning of the term. The option explanations fully identify both swapped concepts.",
                    ),
                    "source": {"deck": "Glossar", "pages": "Pair drill"},
                    "tags": ["Glossar", "Zuordnung"],
                    "_generated": True,
                    "_languages": ["de", "en"],
                }
            )
            pair_index += 1

    return questions


def load_content() -> dict[str, Any]:
    errors: list[str] = []
    questions: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    topics = attach_topic_translations(read_json(CONTENT_DIR / "topics.json"))
    topic_ids = {topic["id"] for topic in topics}
    base_glossary = read_json(CONTENT_DIR / "glossary.json")
    raw_glossary = base_glossary + read_optional_json(
        CONTENT_DIR / "glossary.extra.json", []
    )
    localized_glossary = localize_glossary(raw_glossary)
    translation_payload = read_json(QUESTION_TRANSLATIONS_FILE)
    if translation_payload.get("version") != 1 or not isinstance(
        translation_payload.get("translations"), dict
    ):
        raise ValueError("questions.en.json: ungültiges Übersetzungsformat")
    question_translations = translation_payload["translations"]

    for path in sorted(QUESTION_DIR.glob("*.json")):
        try:
            payload = read_json(path)
            if payload.get("version") != 1:
                raise ValueError("version muss 1 sein")
            entries = payload.get("questions")
            if not isinstance(entries, list):
                raise ValueError("'questions' muss ein Array sein")

            accepted = 0
            for question in entries:
                question = apply_question_translation(
                    question, question_translations.get(question.get("id"))
                )
                validate_question(question, topic_ids)
                question_id = question["id"]
                if question_id in seen_ids:
                    raise ValueError(f"doppelte Frage-ID: {question_id}")
                seen_ids.add(question_id)
                question["_sourceFile"] = path.name
                question["_status"] = question.get("status", "active")
                question["_languages"] = ["de", "en"]
                questions.append(question)
                accepted += 1

            sources.append(
                {
                    "file": path.name,
                    "label": payload.get("label", path.stem),
                    "count": accepted,
                }
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: {exc}")

    glossary = enrich_glossary(localized_glossary, topics, questions)

    generated = []
    try:
        for question in generate_glossary_questions(
            glossary[:BASE_GLOSSARY_QUESTION_COUNT]
        ):
            validate_question(question, topic_ids)
            if question["id"] in seen_ids:
                raise ValueError(f"doppelte generierte Frage-ID: {question['id']}")
            question["_sourceFile"] = "generated-glossary"
            question["_status"] = question.get("status", "active")
            seen_ids.add(question["id"])
            generated.append(question)
        questions.extend(generated)
        sources.append(
            {
                "file": "generated-glossary",
                "label": "Generated glossary drills",
                "count": len(generated),
            }
        )
    except ValueError as exc:
        errors.append(f"generated-glossary: {exc}")

    topics = attach_study_links(topics, glossary, questions)
    cypher_examples = read_optional_json(
        CONTENT_DIR / "cypher_examples.json",
        {"version": 1, "examples": []},
    )

    return {
        "topics": topics,
        "glossary": glossary,
        "questions": questions,
        "cypherExamples": cypher_examples,
        "sources": sources,
        "slides": SLIDES,
        "errors": errors,
    }
