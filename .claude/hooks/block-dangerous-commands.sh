#!/usr/bin/env bash
# Bash 도구 실행 전에 파괴적인 명령을 차단한다.
# PreToolUse(Bash) 훅으로 등록한다. 차단할 때는 exit 2 + stderr 메시지.
#
# 목적은 "실수 방지"다. 우회하려면 얼마든지 가능하므로 완벽한 방어가 아니며,
# 정말 필요한 경우 사용자가 직접 터미널에서 실행하면 된다.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
[ -n "$cmd" ] || exit 0

deny() {
    echo "⛔ 위험한 명령으로 판단되어 차단했습니다: $1" >&2
    echo "   명령: $cmd" >&2
    echo "   의도한 작업이 맞으면 사용자가 직접 터미널에서 실행하세요." >&2
    exit 2
}

# $1 = 사람이 읽을 설명, $2 = grep -E 패턴 (대소문자 무시)
check() {
    if printf '%s' "$cmd" | grep -Eiq "$2"; then
        deny "$1"
    fi
}

# rm -rf / rm -fr / rm -r ... -f  (재귀와 강제가 함께 있을 때)
check "rm 재귀 강제 삭제 (rm -rf)" \
    '(^|[^[:alnum:]_-])rm[[:space:]]+(-[[:alnum:]-]+[[:space:]]+)*-[[:alnum:]]*(rf|fr)([[:space:]]|$)|(^|[^[:alnum:]_-])rm[[:space:]]+-r[[:space:]][^;|&]*-f|(^|[^[:alnum:]_-])rm[[:space:]]+-f[[:space:]][^;|&]*-r'

# git push --force / git push -f  (단, --force-with-lease 는 허용)
check "git 강제 푸시 (git push --force)" \
    '(^|[^[:alnum:]_-])git[[:space:]]+push([[:space:]]+[^;|&]*)?(--force([[:space:]]|$)|[[:space:]]-f([[:space:]]|$))'

# SQL DROP TABLE
check "SQL 테이블 삭제 (DROP TABLE)" \
    '(^|[^[:alnum:]_-])drop[[:space:]]+table([[:space:]]|$)'

# dd if=...  (디스크/파일 저수준 덮어쓰기)
check "dd 저수준 덮어쓰기 (dd if=)" \
    '(^|[^[:alnum:]_-])dd[[:space:]]+([^;|&]*[[:space:]])?if='

exit 0
