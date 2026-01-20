import api from "./api";
import type { StatsResponse } from "./types";

export const getStats = async (): Promise<StatsResponse> => {
  const { data } = await api.get<StatsResponse>('/stats')
  return data
}