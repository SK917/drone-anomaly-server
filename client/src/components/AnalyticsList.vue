<script setup lang="ts">
    import { useAnalyticsStore } from '@/stores/analytics-store';
    import AnalyticsCard from './AnalyticsCard.vue';

    const analyticsStore = useAnalyticsStore();
</script>

<template>
    <div class="flex flex-row gap-2 items-baseline bg-slate-950 rounded-sm overflow-x-auto flex-nowrap w-full p-2 detections-scroll">
            
            <div class="flex-none w-48">
                <AnalyticsCard
                :num="analyticsStore.minDetection?.confidence ?? 0"
                :label="'Lowest Confidence'"
                :otherInfo="'ID: ' + (analyticsStore.minDetection?.track_id ?? 'N/A')"
                :isPercent="true"
                />
            </div>

            <div class="flex-none w-48">
                <AnalyticsCard
                :num="analyticsStore.averageConfidence"
                :label="'Average Confidence'"
                :otherInfo="''"
                :isPercent="true"
                />
            </div>

            <div class="flex-none w-48">
                <AnalyticsCard
                :num="analyticsStore.maxDetection?.confidence ?? 0"
                :label="'Highest Confidence'"
                :otherInfo="'ID: ' + (analyticsStore.maxDetection?.track_id ?? 'N/A')"
                :isPercent="true"
                />
            </div>

            <div class="flex-none w-48">
                <AnalyticsCard
                :num="analyticsStore.totalObjects"
                :label="'Total Objects'"
                :otherInfo="''"
                :isPercent="false"
                />
            </div>

            <div class="flex-none w-48">
                <AnalyticsCard
                :num="analyticsStore.totalDetections"
                :label="'Total Detections'"
                :otherInfo="''"
                :isPercent="false"
                />
            </div>

            <div class="flex-none w-48">
                <AnalyticsCard
                :num="analyticsStore.totalAnomalies"
                :label="'Total Anomalies'"
                :otherInfo="''"
                :isPercent="false"
                />
            </div>

            <div class="flex-none w-48">
                <AnalyticsCard
                :num="analyticsStore.totalObjectDistribution"
                :label="'are Objects'"
                :otherInfo="'of all detections'"
                :isPercent="true"
                />
            </div>

            <div class="flex-none w-48">
                <AnalyticsCard
                :num="analyticsStore.totalAnomalyDistribution"
                :label="'are Anomalies'"
                :otherInfo="'of all detections'"
                :isPercent="true"
                />
            </div>
    </div>
</template>