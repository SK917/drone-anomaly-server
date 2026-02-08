<script setup lang="ts">
    import type { Detection } from '@/services/types';
    import { useAnalyticsStore } from '@/stores/analytics-store';
    import AnalyticsCard from './AnalyticsCard.vue';
    import AnalyticsHeader from './AnalyticsHeader.vue';
    import FrequencyList from './FrequencyList.vue';

    const analyticsStore = useAnalyticsStore();

</script>

<template>
    <div class="flex flex-col">
        <AnalyticsHeader
        label="Confidence"
        :isFirst="true"
        :isSubHeader="false"
        />
        <div class="flex flex-row items-center gap-2">
            <div class="w-full">
                <AnalyticsCard
                :num="analyticsStore.minDetection?.confidence ?? 0"
                :label="'Min Confidence'"
                :otherInfo="'Tracking ID: ' + analyticsStore.minDetection?.track_id"
                :isPercent="true"
                />
            </div>
            <div class="w-full">
                <AnalyticsCard
                :num="analyticsStore.averageConfidence"
                :label="'Average Confidence'"
                :otherInfo="''"
                :isPercent="true"
                />
            </div>
            <div class="w-full">
                <AnalyticsCard
                :num="analyticsStore.maxDetection?.confidence ?? 0"
                :label="'Max Confidence'"
                :otherInfo="'Tracking ID: ' + analyticsStore.maxDetection?.track_id"
                :isPercent="true"
                />
            </div>
        </div>

        <AnalyticsHeader
        label="Detection Counts"
        :isFirst="false"
        :isSubHeader="false"
        />
        <div class="flex flex-row items-center gap-2">
            <div class="w-full">
                <AnalyticsCard
                :num="analyticsStore.totalObjects"
                :label="'Total Objects'"
                :otherInfo="''"
                :isPercent="false"
                />
            </div>
            <div class="w-full">
                <AnalyticsCard
                :num="analyticsStore.totalDetections"
                :label="'Total Detections'"
                :otherInfo="''"
                :isPercent="false"
                />
            </div>
            <div class="w-full">
                <AnalyticsCard
                :num="analyticsStore.totalAnomalies"
                :label="'Total Anomalies'"
                :otherInfo="''"
                :isPercent="false"
                />
            </div>
        </div>
        <div class="flex flex-row items-center gap-2">
            <div class="w-full">
                <AnalyticsCard
                :num="analyticsStore.totalObjectDistribution"
                :label="'Objects'"
                :otherInfo="'of all detections are'"
                :isPercent="true"
                />
            </div>
            <div class="w-full">
                <AnalyticsCard
                :num="analyticsStore.totalAnomalyDistribution"
                :label="'Anomalies'"
                :otherInfo="'of all detections are'"
                :isPercent="true"
                />
            </div>
        </div>

        <AnalyticsHeader
        label="Frequency Counts"
        :isFirst="false"
        :isSubHeader="false"
        />
        <AnalyticsHeader
        label="Anomaly Distribution Across All Anomalies"
        :isFirst="false"
        :isSubHeader="true"
        />
        <FrequencyList
        :items="analyticsStore.anomalyFrequencyByAnomalies"
        />
        <AnalyticsHeader
        label="Anomaly Distribution Across All Detections"
        :isFirst="false"
        :isSubHeader="true"
        />
        <FrequencyList
        :items="analyticsStore.anomalyFrequencyByDetections"
        />
        <AnalyticsHeader
        label="Object Distribution Across All Objects"
        :isFirst="false"
        :isSubHeader="true"
        />
        <FrequencyList
        :items="analyticsStore.objectFrequencyByObjects"
        />
        <AnalyticsHeader
        label="Object Distribution Across All Detections"
        :isFirst="false"
        :isSubHeader="true"
        />
        <FrequencyList
        :items="analyticsStore.objectFrequencyByDetections"
        />
    </div>
</template>