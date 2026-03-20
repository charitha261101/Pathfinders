import React from "react";
import HealthScoreboard from "../components/HealthScoreboard/HealthScoreboard";

/** Standalone route wrapper so HealthScoreboard can be linked as /scoreboard. */
export default function HealthScoreboardPage() {
  return <HealthScoreboard />;
}
