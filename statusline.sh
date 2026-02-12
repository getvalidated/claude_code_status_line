#!/bin/bash
input=$(cat)

dir=$(echo "$input" | jq -r '.workspace.current_dir')
model=$(echo "$input" | jq -r '.model.display_name')
used=$(echo "$input" | jq -r '.context_window.used_percentage // 0')
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')

fast_mode=$(jq -r '.fastMode // false' "$HOME/.claude/settings.json" 2>/dev/null)
if [ "$fast_mode" = "true" ]; then
  fast_indicator=$(printf " \033[38;5;208m↯\033[0m")
else
  fast_indicator=""
fi

branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -n "$branch" ]; then
  ahead=0
  behind=0
  counts=$(git -C "$dir" rev-list --left-right --count HEAD...@{upstream} 2>/dev/null)
  if [ -n "$counts" ]; then
    ahead=$(echo "$counts" | awk '{print $1}')
    behind=$(echo "$counts" | awk '{print $2}')
  fi
  ab_info=""
  if ((ahead > 0 || behind > 0)); then
    ab_info=" "
    if ((ahead > 0)); then
      ab_info+=$(printf "\033[32m↑ %d\033[0m" "$ahead")
    fi
    if ((behind > 0)); then
      if ((ahead > 0)); then ab_info+=" "; fi
      ab_info+=$(printf "\033[31m↓ %d\033[0m" "$behind")
    fi
  fi
  branch_info=$(printf " (on \033[36m\xee\x82\xa0 %s\033[0m%s)" "$branch" "$ab_info")
else
  branch_info=""
fi

cost_fmt=$(printf '$%.2f' "$cost")
if (( $(echo "$cost > 20" | bc -l) )); then
  cost_color=$'\033[1;31m'  # bold red
else
  cost_color=$'\033[1;33m'  # bold yellow
fi

# Today's total from session costs CSV
today=$(TZ=America/Los_Angeles date +%Y-%m-%d)
csv="$HOME/.claude/claude_session_costs.csv"
today_cost=0
if [ -f "$csv" ]; then
  today_cost=$(awk -F, -v d="$today" 'NR>1 && $1==d {s+=$11} END {printf "%.2f", s+0}' "$csv")
fi
today_raw=$(echo "$today_cost + $cost" | bc)
today_cost=$(printf '$%.2f' "$today_raw")
meal_count=$(echo "$today_raw / 20" | bc)
meals=""
if ((meal_count > 0)); then meals=" "; fi
for ((m = 0; m < meal_count; m++)); do meals+="🍗"; done

pct=$(printf "%.0f" "$used")
bar_width=15
filled=$((pct * bar_width / 100))
empty=$((bar_width - filled))

if ((pct < 50)); then
  pct_color=$'\033[1;32m'  # bold green
elif ((pct < 70)); then
  pct_color=$'\033[1;33m'  # bold yellow
else
  pct_color=$'\033[1;31m'  # bold red
fi

bar=""
marker=$((bar_width * 75 / 100))  # 75% compaction threshold
for ((i = 0; i < bar_width; i++)); do
  if ((i == marker)); then
    if ((i < filled)); then
      bar="${bar}"$'\033[38;5;141m'"┽"$'\033[0m'
    else
      bar="${bar}"$'\033[38;5;141m'"┼"$'\033[0m'
    fi
  elif ((i < filled)); then
    bar="${bar}${pct_color}■"$'\033[0m'
  else
    bar="${bar}${pct_color}─"$'\033[0m'
  fi
done
pct_str="${pct_color}$(printf '%.1f%%' "$used")"$'\033[0m'
printf "╭ \033[1m%s\033[0m%s\n╰─➤ %s%s | Context: %s [%s] | Cost: ${cost_color}%s\033[0m (today: %s%s)\n\xe2\x80\x8b" "$dir" "$branch_info" "$model" "$fast_indicator" "$pct_str" "$bar" "$cost_fmt" "$today_cost" "$meals"
