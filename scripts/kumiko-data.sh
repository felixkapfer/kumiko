#!/usr/bin/env bash
# Back up and restore Kumiko's local application data.
# Usage: ./scripts/kumiko-data.sh backup | restore

set -euo pipefail
umask 077

DEFAULT_BACKUP_DIR="$HOME/kumiko-backups"

die() {
  printf 'Fehler: %s\n' "$*" >&2
  exit 1
}

expand_home() {
  case "$1" in
    '~') printf '%s\n' "$HOME" ;;
    '~/'*) printf '%s/%s\n' "$HOME" "${1#~/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

ask_path() {
  local prompt="$1"
  local default="$2"
  local answer
  read -r -p "$prompt [$default]: " answer
  printf '%s\n' "$(expand_home "${answer:-$default}")"
}

confirm() {
  local answer
  read -r -p "$1 [j/N]: " answer
  [[ "$answer" =~ ^([jJyY]|ja|yes)$ ]]
}

require_app_dir() {
  local app_dir="$1"
  [[ -d "$app_dir" ]] || die "App-Ordner existiert nicht: $app_dir"
  [[ -f "$app_dir/server.py" ]] || die "Kein Kumiko-App-Ordner (server.py fehlt): $app_dir"
}

backup() {
  local app_dir backup_dir archive_name archive_path temporary_archive
  app_dir="$(ask_path 'Pfad zum Kumiko-App-Ordner' "$PWD")"
  require_app_dir "$app_dir"
  [[ -d "$app_dir/data" ]] || die "Kein data/-Ordner vorhanden: $app_dir/data"

  backup_dir="$(ask_path 'Ordner für Sicherungen' "$DEFAULT_BACKUP_DIR")"
  mkdir -p "$backup_dir"
  archive_name="kumiko-data-$(date +%Y%m%d-%H%M%S).tar.gz"
  archive_path="$backup_dir/$archive_name"
  temporary_archive="$(mktemp "$backup_dir/.kumiko-data.XXXXXX")"
  trap 'rm -f "$temporary_archive"' EXIT

  tar -C "$app_dir" -czf "$temporary_archive" data
  mv "$temporary_archive" "$archive_path"
  trap - EXIT

  printf 'Sicherung erstellt: %s\n' "$archive_path"
}

restore() {
  local default_archive archive_path app_dir previous_data
  default_archive="$(find "$DEFAULT_BACKUP_DIR" -maxdepth 1 -type f -name 'kumiko-data-*.tar.gz' -print 2>/dev/null | sort | tail -n 1 || true)"
  [[ -n "$default_archive" ]] || default_archive="$DEFAULT_BACKUP_DIR/kumiko-data-YYYYMMDD-HHMMSS.tar.gz"
  archive_path="$(ask_path 'Pfad zur Sicherungsdatei' "$default_archive")"
  [[ -f "$archive_path" ]] || die "Sicherungsdatei existiert nicht: $archive_path"
  tar -tzf "$archive_path" | grep -Eq '^data(/|$)' || die 'Archiv enthält keinen data/-Ordner.'

  app_dir="$(ask_path 'Pfad zum Kumiko-App-Ordner, in den wiederhergestellt wird' "$PWD")"
  require_app_dir "$app_dir"

  if [[ -e "$app_dir/data" ]]; then
    previous_data="$app_dir/data.before-restore-$(date +%Y%m%d-%H%M%S)"
    confirm "Vorhandene Daten werden nach $(basename "$previous_data") verschoben. Fortfahren?" || {
      printf 'Wiederherstellung abgebrochen.\n'
      exit 0
    }
    mv "$app_dir/data" "$previous_data"
  fi

  tar -C "$app_dir" --no-same-owner -xzf "$archive_path"
  printf 'Daten wiederhergestellt nach: %s/data\n' "$app_dir"
}

case "${1:-}" in
  backup) backup ;;
  restore) restore ;;
  *)
    printf 'Verwendung: %s {backup|restore}\n' "${0##*/}" >&2
    exit 2
    ;;
esac
