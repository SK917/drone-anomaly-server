import api from "./api";
import type { DetectionsResponse } from "./types";

export const getDetections = async (): Promise<DetectionsResponse> => {
  const { data } = await api.get<DetectionsResponse>('/detections')
  return data
}