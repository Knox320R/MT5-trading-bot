// Trade Marker Plugin - Draws trade arrows on chart
const tradeMarkerPlugin = {
    id: 'tradeMarkers',
    afterDatasetsDraw: function(chart) {
        const ctx = chart.ctx;

        // Find marker datasets
        const buyDataset = chart.data.datasets.find(ds => ds.label === 'BUY Trades');
        const sellDataset = chart.data.datasets.find(ds => ds.label === 'SELL Trades');

        if (!buyDataset && !sellDataset) {
           return;
        }

        // Draw BUY markers (green downward triangles)
        if (buyDataset && buyDataset.data) {
           buyDataset.data.forEach((marker, idx) => {
                if (!marker || marker.x === undefined || marker.y === undefined) {
                   return;
                }

                const barIndex = marker.x;
                const price = marker.y;

                // Get pixel position
                const meta = chart.getDatasetMeta(1); // Body dataset
                if (!meta.data[barIndex]) {
                   return;
                }

                const xPixel = meta.data[barIndex].x;

                // Get Y coordinate from the actual candle bar instead of scale
                const barElement = meta.data[barIndex];
                const yPixel = barElement.y;

                // Draw green downward arrow emoji
                ctx.save();
                ctx.fillStyle = '#00cc00';
                ctx.font = '20px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('⬇', xPixel, 40);
                ctx.restore();
            });
        }

        // Draw SELL markers (red upward triangles)
        if (sellDataset && sellDataset.data) {
           sellDataset.data.forEach((marker, idx) => {
                if (!marker || marker.x === undefined || marker.y === undefined) {
                   return;
                }

                const barIndex = marker.x;
                const price = marker.y;

                // Get pixel position
                const meta = chart.getDatasetMeta(1); // Body dataset
                if (!meta.data[barIndex]) {
                   return;
                }

                const xPixel = meta.data[barIndex].x;

                // Get Y coordinate from the actual candle bar instead of scale
                const barElement = meta.data[barIndex];
                const yPixel = barElement.y;

                // Draw red upward arrow emoji
                ctx.save();
                ctx.fillStyle = '#cc0000';
                ctx.font = '20px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('⬆', xPixel, 30);
                ctx.restore();
            });
        }

   }
};
