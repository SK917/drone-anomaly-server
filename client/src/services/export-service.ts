import { useStatsStore } from '@/stores/stats-store';
import { useAnalyticsStore } from '@/stores/analytics-store';
import { useDetectionsStore } from '@/stores/detections-store';
import { useAnomaliesStore } from '@/stores/anomalies-store';
import { useExportStore } from '@/stores/export-store';
import type { Anomaly } from '@/services/types';

function generateLogId(): string {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let id = '';
    for (let i = 0; i < 6; i++) {
        id += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return id;
}

function sortByTrackId(anomalies: Anomaly[]): Anomaly[] {
    return [...anomalies].sort((a, b) => (a.track_id ?? 0) - (b.track_id ?? 0));
}

function pad(label: string, width: number = 36): string {
    return label.padEnd(width);
}

function padDeep(label: string, width: number = 36): string {
    return label.padEnd(width);
}

function sectionHeader(label: string): string {
    const totalWidth = 49;
    const prefix = `━━━ ${label} `;
    const remaining = totalWidth - prefix.length;
    return prefix + '━'.repeat(Math.max(0, remaining));
}

function triggerDownload(content: string, filename: string, mimeType: string) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.target = '_blank';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function generateTxt(logId: string): string {
    const statsStore = useStatsStore();
    const analyticsStore = useAnalyticsStore();
    const detectionsStore = useDetectionsStore();
    const anomaliesStore = useAnomaliesStore();
    const exportStore = useExportStore();
    const req = exportStore.exportRequest;

    const timestamp = new Date().toLocaleString();
    const lines: string[] = [];

    lines.push('════════════════════════════════════════════════');
    lines.push('         ANOMALY DETECTION EXPORT LOG           ');
    lines.push('════════════════════════════════════════════════');
    lines.push('');
    lines.push(`  Log ID    : ${logId}`);
    lines.push(`  Generated : ${timestamp}`);
    lines.push('');

    if (req.current_stream_stats) {
        lines.push(sectionHeader('STREAM STATISTICS'));
        lines.push('');
        lines.push(`  ${pad('Inference Count:')} ${statsStore.interference_count ?? 'N/A'}`);
        lines.push(`  ${pad('Inference FPS:')} ${statsStore.interference_fps?.toFixed(2) ?? 'N/A'}`);
        lines.push('');
    }

    if (req.stats_summary) {
        lines.push(sectionHeader('GENERAL STATISTICS'));
        lines.push('');
        lines.push(`  ${pad('Total Detections:')} ${analyticsStore.totalDetections}`);
        lines.push(`  ${pad('Total Objects:')} ${analyticsStore.totalObjects}`);
        lines.push(`  ${pad('Total Anomalies:')} ${analyticsStore.totalAnomalies}`);
        lines.push(`  ${pad('Objects % of Detections:')} ${(analyticsStore.totalObjectDistribution * 100).toFixed(2)}%`);
        lines.push(`  ${pad('Anomalies % of Detections:')} ${(analyticsStore.totalAnomalyDistribution * 100).toFixed(2)}%`);
        lines.push('');
        lines.push(`  ${pad('Average Confidence:')} ${(analyticsStore.averageConfidence * 100).toFixed(2)}%`);
        lines.push('');
        lines.push('  Highest Confidence Detection:');
        lines.push(`    ${padDeep('Track ID:')} ${analyticsStore.maxDetection?.track_id ?? 'N/A'}`);
        lines.push(`    ${padDeep('Class:')} ${analyticsStore.maxDetection?.class_name ?? 'N/A'}`);
        lines.push(`    ${padDeep('Confidence:')} ${analyticsStore.maxDetection ? (analyticsStore.maxDetection.confidence * 100).toFixed(2) + '%' : 'N/A'}`);
        lines.push(`    ${padDeep('Type:')} ${analyticsStore.maxDetection?.is_anomaly ? 'Anomaly' : 'Object'}`);
        lines.push('');
        lines.push('  Lowest Confidence Detection:');
        lines.push(`    ${padDeep('Track ID:')} ${analyticsStore.minDetection?.track_id ?? 'N/A'}`);
        lines.push(`    ${padDeep('Class:')} ${analyticsStore.minDetection?.class_name ?? 'N/A'}`);
        lines.push(`    ${padDeep('Confidence:')} ${analyticsStore.minDetection ? (analyticsStore.minDetection.confidence * 100).toFixed(2) + '%' : 'N/A'}`);
        lines.push(`    ${padDeep('Type:')} ${analyticsStore.minDetection?.is_anomaly ? 'Anomaly' : 'Object'}`);
        lines.push('');
    }

    if (req.detections_summary) {
        lines.push(sectionHeader('DETECTIONS SUMMARY'));
        lines.push('');
        const entries = detectionsStore.groupedDetectionsSorted;
        entries.forEach((entry, i) => {
            const det = entry.detection;
            const freqByType = det.is_anomaly
                ? analyticsStore.getFrequencyFromList(analyticsStore.anomalyFrequencyByAnomalies, det.class_id)
                : analyticsStore.getFrequencyFromList(analyticsStore.objectFrequencyByObjects, det.class_id);
            const freqByDetections = det.is_anomaly
                ? analyticsStore.getFrequencyFromList(analyticsStore.anomalyFrequencyByDetections, det.class_id)
                : analyticsStore.getFrequencyFromList(analyticsStore.objectFrequencyByDetections, det.class_id);

            lines.push(`  [${String(i + 1).padStart(3, '0')}] ${det.class_name.toUpperCase()} (${det.is_anomaly ? 'Anomaly' : 'Object'})`);
            lines.push(`        ${padDeep('Times Seen:')} ${entry.numDetects}`);
            lines.push(`        ${padDeep('Highest Confidence:')} ${(det.confidence * 100).toFixed(2)}%`);
            lines.push(`        ${padDeep('Freq. Among Type:')} ${freqByType.toFixed(2)}%`);
            lines.push(`        ${padDeep('Freq. Among Detections:')} ${freqByDetections.toFixed(2)}%`);
            lines.push('');
        });
    }

    if (req.all_anomalies || req.selected_anomalies) {
        const anomalies = req.all_anomalies
            ? sortByTrackId(anomaliesStore.anomalies)
            : sortByTrackId(exportStore.selectedAnomalies);

        const label = req.all_anomalies ? 'ALL ANOMALIES' : 'SELECTED ANOMALIES';
        lines.push(sectionHeader(label));
        lines.push('');

        if (anomalies.length === 0) {
            lines.push('  No anomalies recorded.');
            lines.push('');
        } else {
            anomalies.forEach((anomaly, i) => {
                lines.push(`  [${String(i + 1).padStart(3, '0')}]`);
                lines.push(`        ${padDeep('Track ID:')} ${anomaly.track_id}`);
                lines.push(`        ${padDeep('Class ID:')} ${anomaly.class_id}`);
                lines.push(`        ${padDeep('Class:')} ${anomaly.class_name}`);
                lines.push(`        ${padDeep('Confidence:')} ${(anomaly.confidence * 100).toFixed(2)}%`);
                lines.push(`        ${padDeep('BBox:')} ${anomaly.bbox.map(v => Math.round(v)).join(', ')}`);
                lines.push(`        ${padDeep('Timestamp:')} ${new Date(anomaly.timestamp * 1000).toLocaleString()}`);
                lines.push('');
            });
        }
    }

    lines.push(sectionHeader('END OF LOG'));
    return lines.join('\n');
}

function generateJson(logId: string): object {
    const statsStore = useStatsStore();
    const analyticsStore = useAnalyticsStore();
    const detectionsStore = useDetectionsStore();
    const anomaliesStore = useAnomaliesStore();
    const exportStore = useExportStore();
    const req = exportStore.exportRequest;

    const output: Record<string, any> = {
        log_id: logId,
        generated_at: new Date().toISOString(),
    };

    if (req.current_stream_stats) {
        output.stream_statistics = {
            inference_count: statsStore.interference_count ?? null,
            inference_fps: statsStore.interference_fps ?? null,
        };
    }

    if (req.stats_summary) {
        output.general_statistics = {
            total_detections: analyticsStore.totalDetections,
            total_objects: analyticsStore.totalObjects,
            total_anomalies: analyticsStore.totalAnomalies,
            object_distribution: Number((analyticsStore.totalObjectDistribution * 100).toFixed(2)),
            anomaly_distribution: Number((analyticsStore.totalAnomalyDistribution * 100).toFixed(2)),
            average_confidence: Number((analyticsStore.averageConfidence * 100).toFixed(2)),
            highest_confidence_detection: analyticsStore.maxDetection ? {
                track_id: analyticsStore.maxDetection.track_id,
                class_id: analyticsStore.maxDetection.class_id,
                class_name: analyticsStore.maxDetection.class_name,
                confidence: Number((analyticsStore.maxDetection.confidence * 100).toFixed(2)),
                is_anomaly: analyticsStore.maxDetection.is_anomaly,
            } : null,
            lowest_confidence_detection: analyticsStore.minDetection ? {
                track_id: analyticsStore.minDetection.track_id,
                class_id: analyticsStore.minDetection.class_id,
                class_name: analyticsStore.minDetection.class_name,
                confidence: Number((analyticsStore.minDetection.confidence * 100).toFixed(2)),
                is_anomaly: analyticsStore.minDetection.is_anomaly,
            } : null,
        };
    }

    if (req.detections_summary) {
        output.detections_summary = detectionsStore.groupedDetectionsSorted.map((entry, i) => {
            const det = entry.detection;
            const freqByType = det.is_anomaly
                ? analyticsStore.getFrequencyFromList(analyticsStore.anomalyFrequencyByAnomalies, det.class_id)
                : analyticsStore.getFrequencyFromList(analyticsStore.objectFrequencyByObjects, det.class_id);
            const freqByDetections = det.is_anomaly
                ? analyticsStore.getFrequencyFromList(analyticsStore.anomalyFrequencyByDetections, det.class_id)
                : analyticsStore.getFrequencyFromList(analyticsStore.objectFrequencyByDetections, det.class_id);

            return {
                index: i + 1,
                class_id: det.class_id,
                class_name: det.class_name,
                is_anomaly: det.is_anomaly,
                times_seen: entry.numDetects,
                highest_confidence: Number((det.confidence * 100).toFixed(2)),
                frequency_among_type: Number(freqByType.toFixed(2)),
                frequency_among_detections: Number(freqByDetections.toFixed(2)),
            };
        });
    }

    if (req.all_anomalies || req.selected_anomalies) {
        const anomalies = req.all_anomalies
            ? sortByTrackId(anomaliesStore.anomalies)
            : sortByTrackId(exportStore.selectedAnomalies);

        output.anomalies = anomalies.map((anomaly, i) => ({
            index: i + 1,
            track_id: anomaly.track_id,
            class_id: anomaly.class_id,
            class_name: anomaly.class_name,
            confidence: Number((anomaly.confidence * 100).toFixed(2)),
            bbox: anomaly.bbox.map(v => Math.round(v)),
            timestamp: new Date(anomaly.timestamp * 1000).toISOString(),
        }));
    }

    return output;
}

export function exportData() {
    const exportStore = useExportStore();
    const req = exportStore.exportRequest;
    const logId = generateLogId();

    if (req.is_txt) {
        const content = generateTxt(logId);
        triggerDownload(content, `anomaly-log-${logId}.txt`, 'text/plain');
    } else if (req.is_json) {
        const content = JSON.stringify(generateJson(logId), null, 2);
        triggerDownload(content, `anomaly-log-${logId}.json`, 'application/json');
    }

    exportStore.resetExportRequest();
}