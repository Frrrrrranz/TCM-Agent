export type ToolProfile = 'coding' | 'tcm-consultation'

export const TCM_CONSULTATION_MCP_SERVERS = new Set(['tcm-data-engine'])

export function isConsultationProfile(profile: ToolProfile): boolean {
  return profile === 'tcm-consultation'
}
