//Control which state is displayed on the page
function showOnly(state) {
    const loadingState = document.getElementById("loadingState");
    const emptyState = document.getElementById("emptyState");
    const errorState = document.getElementById("errorState");
    const trialTable = document.getElementById("trialTable");

    //Only show loading when state is loading.
    loadingState.style.display =
        state === "loading" ? "block" : "none";

    //Only show empty message when state is empty
    emptyState.style.display =
        state === "empty" ? "block" : "none";

    //Only show error message when state is error.
    errorState.style.display =
        state === "error" ? "block" : "none";

    //Only show table when state is table
    trialTable.style.display =
        state === "table" ? "table" : "none";
}


//Put trial data into the HTML table.
function renderRows(data) {
    const tbody = document.getElementById("trialTableBody");

    //Clear old rows before adding new rows
    tbody.innerHTML = "";

    //Go through every trial returned by API.
    for (const trial of data) {
        //Create a new HTML table row
        const row = document.createElement("tr");

        //Put current trial information and buttons into the row.
        row.innerHTML = `
            <td>${trial.id}</td>
            <td>${trial.brief_title}</td>
            <td>${trial.sponsor}</td>
            <td>
                <button
                    type="button"
                    class="editBtn"
                    data-id="${trial.id}"
                >
                    Edit
                </button>

                <button
                    type="button"
                    class="deleteBtn"
                    data-id="${trial.id}"
                >
                    Delete
                </button>
            </td>
        `;

        //Add the row into table body
        tbody.appendChild(row);
    }
}


//Load trials from FastAPI
async function loadTrials(query = "") {
    //Show loading before sending request.
    showOnly("loading");

    try {
        //Use search API when query is not empty.
        const url = query
            ? `/api/trials?q=${encodeURIComponent(query)}`
            : "/api/trials";

        //Send GET request to FastAPI
        const response = await fetch(url);

        //fetch does not throw error for 404 or 500 automatically.
        if (!response.ok) {
            throw new Error(
                "Request failed: HTTP " + response.status
            );
        }

        //Read JSON response and change it into JavaScript data
        const data = await response.json();

        //Print returned data for debugging.
        console.log(data);

        //Show empty state if API returns an empty array
        if (data.length === 0) {
            showOnly("empty");
            return;
        }

        //Create rows and show the table.
        renderRows(data);
        showOnly("table");

    } catch (error) {
        //Find the error message area
        const errorState = document.getElementById("errorState");

        //Display error message on the page.
        errorState.textContent =
            "Unable to load trials: " + error.message;

        showOnly("error");

        //Print complete error in Console
        console.error(error);
    }
}


//Get createForm from HTML
const createForm = document.getElementById("createForm");


//Run this function when user submits the form.
createForm.addEventListener("submit", async (event) => {
    //Stop the default form submission and page refresh
    event.preventDefault();

    //Get the two input elements.
    const newTitleInput = document.getElementById("newTitle");
    const newSponsorInput = document.getElementById("newSponsor");

    //Read values from the input elements
    const briefTitle = newTitleInput.value.trim();
    const sponsor = newSponsorInput.value.trim();

    //Show loading before sending POST request.
    showOnly("loading");

    try {
        //Send new trial data to FastAPI
        const response = await fetch("/api/trials", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                brief_title: briefTitle,
                sponsor: sponsor
            })
        });

        //Throw error if create request failed
        if (!response.ok) {
            throw new Error(
                "Create request failed: HTTP "
                + response.status
            );
        }

        //Read the trial created by FastAPI.
        const createdTrial = await response.json();

        //Print created trial for debugging
        console.log("Created trial:", createdTrial);

        //Clear the two input boxes.
        newTitleInput.value = "";
        newSponsorInput.value = "";

        //Reload the table to show the new trial
        await loadTrials();

    } catch (error) {
        //Show error message if POST request failed.
        const errorState = document.getElementById("errorState");

        errorState.textContent =
            "Unable to create trial: " + error.message;

        showOnly("error");
        console.error(error);
    }
});


//Get table body for event delegation
const trialTableBody = document.getElementById("trialTableBody");


//Handle Edit and Delete button clicks
trialTableBody.addEventListener("click", async (event) => {
    //Find the button that user clicked.
    const button = event.target.closest("button");

    //Stop if user did not click a button
    if (!button) {
        return;
    }

    //Read trial id from the button's data-id.
    const trialId = button.dataset.id;

    //Find the table row containing this button
    const row = button.closest("tr");

    try {
        //Run update logic when user clicks Edit.
        if (button.classList.contains("editBtn")) {
            //Read current title and sponsor from table row
            const currentTitle =
                row.children[1].textContent.trim();

            const currentSponsor =
                row.children[2].textContent.trim();

            //Ask user to enter a new title.
            const newTitle = prompt(
                "Enter the new brief title:",
                currentTitle
            );

            //Stop updating if user clicks Cancel
            if (newTitle === null) {
                return;
            }

            //Ask user to enter a new sponsor.
            const newSponsor = prompt(
                "Enter the new sponsor:",
                currentSponsor
            );

            //Stop updating if user clicks Cancel
            if (newSponsor === null) {
                return;
            }

            //Remove spaces from beginning and end.
            const cleanTitle = newTitle.trim();
            const cleanSponsor = newSponsor.trim();

            //Do not send empty values to FastAPI.
            if (!cleanTitle || !cleanSponsor) {
                throw new Error(
                    "Title and sponsor cannot be empty."
                );
            }

            //Show loading while sending PUT request
            showOnly("loading");

            //Send updated data to FastAPI.
            const response = await fetch(
                `/api/trials/${trialId}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        brief_title: cleanTitle,
                        sponsor: cleanSponsor
                    })
                }
            );

            //Throw error if update request failed.
            if (!response.ok) {
                throw new Error(
                    "Update request failed: HTTP "
                    + response.status
                );
            }

            //Read and print the updated trial
            const updatedTrial = await response.json();
            console.log("Updated trial:", updatedTrial);

            //Reload the table after updating.
            await loadTrials();
        }

        //Run delete logic when user clicks Delete.
        if (button.classList.contains("deleteBtn")) {
            //Ask user to confirm before deleting
            const confirmed = confirm(
                "Are you sure you want to delete this trial?"
            );

            //Stop deleting if user clicks Cancel.
            if (!confirmed) {
                return;
            }

            //Show loading while sending DELETE request
            showOnly("loading");

            //Send DELETE request to FastAPI.
            const response = await fetch(
                `/api/trials/${trialId}`,
                {
                    method: "DELETE"
                }
            );

            //Throw error if delete request failed.
            if (!response.ok) {
                throw new Error(
                    "Delete request failed: HTTP "
                    + response.status
                );
            }

            //Read and print the delete result
            const deletedResult = await response.json();
            console.log("Deleted trial:", deletedResult);

            //Reload the table after deleting.
            await loadTrials();
        }

    } catch (error) {
        //Show error if update or delete request failed.
        const errorState = document.getElementById("errorState");

        errorState.textContent =
            "Request failed: " + error.message;

        showOnly("error");
        console.error(error);
    }
});


//Get search elements from HTML
const searchInput = document.getElementById("searchInput");
const searchButton = document.getElementById("searchButton");
const clearSearchButton = document.getElementById(
    "clearSearchButton"
);


//Run search when user clicks Search button.
searchButton.addEventListener("click", async () => {
    //Read and clean the search text
    const query = searchInput.value.trim();

    //Load trials matching this search text.
    await loadTrials(query);
});


//Clear search and display all trials
clearSearchButton.addEventListener("click", async () => {
    //Clear the search input.
    searchInput.value = "";

    //Load all trials without a search query
    await loadTrials();
});


//Load trials when page opens
loadTrials();