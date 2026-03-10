import api from "./api";
import type { AnomaliesResponse } from "./types";

export const getAnomalies = async (): Promise<AnomaliesResponse> => {
  const { data } = await api.get<AnomaliesResponse>('/anomalies')
  return data
}