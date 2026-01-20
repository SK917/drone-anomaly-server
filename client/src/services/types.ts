export interface Detection {
    class_id: number
    class_name: string
    confidence: number
    bbox: [number, number, number, number]
    is_anomaly: boolean
}

export interface DetectionsResponse {
    timestamp: number
    num_detections: number
    detections: Detection[]
    inference_count: number
    inference_fps: number
    has_anomaly: boolean
    anomaly_count: number
}

export interface StatsResponse {
    interference_count: number
    interference_fps: number
    has_stream: boolean
    is_processing: boolean
}