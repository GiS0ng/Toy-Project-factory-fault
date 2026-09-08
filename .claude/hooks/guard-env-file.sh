#!/usr/bin/env bash
# 비밀키·인증서 파일을 Claude가 직접 쓰는 것을 막는다 (AGENTS.md: 비밀키는 환경 변수로 관리).
# PreToolUse(Write|Edit) 훅으로 등록한다.
#
# .env 자체와 패키지 관리 파일은 여기서 막지 않고 require-approval.sh 가
# "사용자 승인 필요(ask)" 로 처리한다. 이 훅은 절대 쓰면 안 되는 자격 증명만 하드 차단한다.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')
[ -n "$file" ] || exit 0

base=$(basename "$file")
case "$base" in
    *.pem | *.key | *.p12 | *.pfx | *.keystore | *.jks | id_rsa | id_dsa | id_ecdsa | id_ed25519 | .env.local | .env.*.local | .env.production | .env.prod)
        echo "⛔ '$base' 은(는) 자격 증명 파일이라 훅으로 편집을 막고 있습니다 (AGENTS.md)." >&2
        echo "   필요하면 사람이 직접 터미널에서 수정하세요." >&2
        exit 2
        ;;
esac

exit 0
