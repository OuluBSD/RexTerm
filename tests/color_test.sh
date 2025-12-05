#!/usr/bin/env bash
set -euo pipefail

section() {
  printf "\n=== %s ===\n" "$*"
}

section "Environment"
printf "TERM=%s COLORTERM=%s\n" "${TERM:-}" "${COLORTERM:-}"

section "16 colors (foreground on default background)"
for code in $(seq 0 15); do
  printf "\e[38;5;%sm%3s " "$code" "$code"
done
printf "\e[0m\n"

section "16 colors (background with inverse text)"
for code in $(seq 0 15); do
  printf "\e[48;5;%sm\e[38;5;0m %3s \e[0m" "$code" "$code"
done
printf "\n"

section "256-color palette (background swatches)"
for row in $(seq 0 15); do
  for col in $(seq 0 15); do
    code=$((row * 16 + col))
    printf "\e[48;5;%sm\e[38;5;%sm %3s \e[0m" "$code" "$([ $code -lt 16 ] && echo 15 || echo 0)" "$code"
  done
  printf "\n"
done

section "Truecolor gradient (background)"
for g in $(seq 0 5 255); do
  for r in $(seq 0 5 255); do
    b=$((255 - g))
    printf "\e[48;2;%s;%s;%sm " "$r" "$g" "$b"
  done
  printf "\e[0m\n"
done

section "Truecolor blocks (foreground)"
for r in 0 95 135 175 215 255; do
  for g in 0 95 135 175 215 255; do
    for b in 0 95 135 175 215 255; do
      printf "\e[38;2;%s;%s;%sm●" "$r" "$g" "$b"
    done
    printf " "
  done
  printf "\e[0m\n"
done

printf "\nDone. Resetting colors.\e[0m\n"
