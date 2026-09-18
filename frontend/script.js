document.getElementById("predict-btn").addEventListener("click", async () => {
  const url = document.getElementById("url").value;
  const votingType = document.getElementById("voting-type").value;
  const resultDiv = document.getElementById("result");
  const predictionText = document.getElementById("prediction");
  const confidenceText = document.getElementById("confidence");

  resultDiv.style.display = "none";
  predictionText.textContent = "";
  confidenceText.textContent = "";

  if (!url) {
    alert("Please enter a URL.");
    return;
  }

  try {
    const response = await fetch(`/predict-${votingType}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      throw new Error("Failed to get prediction. Please try again.");
    }

    const data = await response.json();

    predictionText.textContent = `Prediction: ${data.prediction}`;
    confidenceText.textContent = data.probability
      ? `Confidence: ${(data.probability * 100).toFixed(2)}%`
      : "";

    predictionText.style.color = data.prediction === "safe" ? "green" : "red";
    resultDiv.style.display = "block";
  } catch (error) {
    alert(error.message);
  }
});