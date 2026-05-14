#!/bin/bash
# Safe key/value config loader for IP-Sentinel Agent.
# Avoids executing config files as shell code.

safe_load_config() {
    local file="$1"
    local line key value
    [ -f "$file" ] || return 1

    while IFS= read -r line || [ -n "$line" ]; do
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [ -z "$line" ] && continue
        case "$line" in \#*) continue ;; esac
        case "$line" in *=*) ;; *) continue ;; esac

        key="${line%%=*}"
        value="${line#*=}"
        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        case "$key" in
            AGENT_VERSION|REGION_CODE|REGION_NAME|BASE_LAT|BASE_LON|LANG_PARAMS|VALID_URL_SUFFIX|ENABLE_GOOGLE|ENABLE_TRUST|TG_TOKEN|TG_API_URL|CHAT_ID|WEBHOOK_SECRET|AGENT_PORT|INSTALL_DIR|LOG_FILE|IP_PREF|PUBLIC_IP|BIND_IP|NODE_NAME|NODE_ALIAS|ENABLE_OTA|REPO_OWNER|REPO_NAME|REPO_REF|REPO_RAW_URL) ;;
            *) continue ;;
        esac

        value="${value#"${value%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"
        if [ "${value#\"}" != "$value" ] && [ "${value%\"}" != "$value" ]; then
            value="${value#\"}"
            value="${value%\"}"
        elif [ "${value#\'}" != "$value" ] && [ "${value%\'}" != "$value" ]; then
            value="${value#\'}"
            value="${value%\'}"
        fi

        # Reject command substitution, chaining, pipes, redirection, and control chars.
        case "$value" in
            *[");"\&\|\<\>\`\$]*|*$'\n'*|*$'\r'*) continue ;;
        esac

        export "$key=$value"
    done < "$file"
}
