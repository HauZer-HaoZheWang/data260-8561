function makeSubmission() {
  let count = 0;
  return function () {
    count = count + 1;
    return count;
  };
}


const countSubmission = makeSubmission();


const trialForm = document.getElementById("trialForm");

trialForm.addEventListener("submit", (event) => {

  event.preventDefault();

  const detailedDescription = document.getElementById("detailedDescription").value;
  if (detailedDescription.length <= 25) {
    alert("Your detailed description must more than 25 characters.");
    return;
  }

  const agreeTerms = document.getElementById("agreeTerms").checked;
  if (!agreeTerms) {
    alert("Please check 'I agree to the terms and conditions.'");
    return;
  }

  const trialData = Object.fromEntries(new FormData(trialForm));
  const jsonString = JSON.stringify(trialData);
  console.log("Submitted JSON:", jsonString);

  const parsed = JSON.parse(jsonString);
  const { briefTitle, submitterEmail } = parsed;
  console.log("Brief Title:", briefTitle);
  console.log("Submitter Email:", submitterEmail);
 
  const withDate = { ...parsed, submissionDate: new Date().toISOString() };
  console.log("With date:", withDate);

  const total = countSubmission();
  console.log("Submission count:", total);
});