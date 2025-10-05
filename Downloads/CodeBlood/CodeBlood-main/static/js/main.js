document.addEventListener('DOMContentLoaded', () => {
  const visualizeButtons = document.querySelectorAll('.visualize-btn');
  const ctx = document.getElementById('attendanceChart').getContext('2d');
  let attendanceChart = null;

  visualizeButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const runId = button.getAttribute('data-run-id');
      if (!runId) {
        alert('Run ID not found for visualization.');
        return;
      }

      try {
        const response = await fetch(`/attendance-data/${runId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch attendance data.');
        }
        const data = await response.json();

        // Data expected: { presentCount: number, absentCount: number }
        const chartData = {
          labels: ['Present', 'Absent'],
          datasets: [{
            data: [data.presentCount, data.absentCount],
            backgroundColor: ['#4ade80', '#f87171'], // green and red
            hoverOffset: 30
          }]
        };

        if (attendanceChart) {
          attendanceChart.destroy();
        }

        attendanceChart = new Chart(ctx, {
          type: 'pie',
          data: chartData,
          options: {
            responsive: true,
            plugins: {
              legend: {
                position: 'bottom',
              },
              title: {
                display: true,
                text: 'Attendance Visualization'
              }
            }
          }
        });
      } catch (error) {
        alert('Error loading attendance data: ' + error.message);
      }
    });
  });
});
