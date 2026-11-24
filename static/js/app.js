/* Smart Malaysia Travel Recommendation System */

let currentUser = null;
let allDestinations = [];
let favouriteIds = new Set();
let latestRecommendations = [];
let savedTravelPreferences = null;

/* SECTION: FESTIVAL MODE STATE */
let festivalMode = false;
let selectedFestivalId = "deepavali";
let festivalOffers = [];
let focusedFestivalDestinationId = null;

/* INITIALIZATION */

document.addEventListener("DOMContentLoaded", () => {
    setupEventListeners();
    switchTab("recommendations");
    loadFestivalPromotions();
});

function setupEventListeners() {
    document.getElementById("login-button")
        ?.addEventListener("click", loginUser);

    document.getElementById("logout-button")
        ?.addEventListener("click", logout);

    // Open Admin Dashboard
    document.getElementById("admin-dashboard-button")
        ?.addEventListener("click", function () {
            window.location.href = "/admin";
        });

    document.getElementById("festival-mode-button")
        ?.addEventListener("click", () => setFestivalMode(true));
    document.getElementById("exit-festival-button")
        ?.addEventListener("click", () => setFestivalMode(false));
    document.getElementById("festival-select")
        ?.addEventListener("change", async (event) => {
            selectedFestivalId = event.target.value;
            updateFestivalColourTheme();
            updateExploreFestivalHeader();
            renderFestivalDeals();
            refreshFestivalPrices();
            if (document.getElementById("recommendations-tab")?.classList.contains("active") && festivalMode) {
                await generateRecommendations();
            }
        });
    document.getElementById("festival-deals-list")
        ?.addEventListener("click", event => {
            const button = event.target.closest("[data-festival-destination]");
            if (button) openFestivalDestination(button.dataset.festivalDestination);
        });
    document.getElementById("back-to-festival-button")
        ?.addEventListener("click", () => { focusedFestivalDestinationId = null; switchTab("festival"); });
    document.getElementById("explore-view-deals")
        ?.addEventListener("click", () => { focusedFestivalDestinationId = null; switchTab("festival"); });

    document.getElementById("user-id")
        ?.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                loginUser();
            }
        });

    document.querySelectorAll(".tab-button").forEach(button => {
        button.addEventListener("click", () => {
            switchTab(button.dataset.tab);
        });
    });

    document.getElementById("travel-preferences-form")
        ?.addEventListener("submit", (event) => {
            event.preventDefault();
            savePreferences();
        });

    // Update category/activity availability as preferences change.
    ["budget-input", "duration-input", "category-select", "region-select",
     "style-select", "companion-select"].forEach(id => {
        const field = document.getElementById(id);
        field?.addEventListener("input", updateSmartAvailability);
        field?.addEventListener("change", updateSmartAvailability);
    });
    document.getElementById("activities-options")
        ?.addEventListener("change", updateSmartAvailability);

    document.getElementById("recommend-button")
        ?.addEventListener("click", generateRecommendations);

    document.getElementById("recommendations-list")
        ?.addEventListener("click", handleFavouriteClick);

    document.getElementById("favourites-list")
        ?.addEventListener("click", handleFavouriteClick);

    document.getElementById("all-destinations-list")
        ?.addEventListener("click", handleFavouriteClick);

    /* DESTINATION SEARCH AND FILTERS */

    document.getElementById("destination-search")
        ?.addEventListener("input", filterDestinations);

    document.getElementById("state-filter")
        ?.addEventListener("change", handleExploreStateChange);

    document.getElementById("region-filter")
        ?.addEventListener("change", handleExploreRegionChange);

    document.getElementById("clear-filters-button")
        ?.addEventListener("click", clearDestinationFilters);

    /* Prices are controlled by the saved Travel Preferences only. */
    ["festival-affordable", "festival-sort"].forEach(id =>
        document.getElementById(id)?.addEventListener("change", renderFestivalDeals));
    document.getElementById("explore-affordable")?.addEventListener("change", filterDestinations);
}

/* API HELPER */

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    const data = await response.json();

    if (!response.ok || data?.success === false) {
        throw new Error(
            data?.error || `Request failed (${response.status})`
        );
    }

    return data;
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function showMessage(elementId, message, isError = false) {
    const element = document.getElementById(elementId);

    if (!element) return;

    element.textContent = message;
    element.style.color = isError ? "#d94c4c" : "#087f72";
}

function showLoading(container) {
    if (container) {
        container.innerHTML =
            '<div class="loading">Loading, please wait...</div>';
    }
}

function showEmpty(container, message) {
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <p>${escapeHTML(message)}</p>
            </div>
        `;
    }
}

/* USER LOGIN / LOGOUT */

async function loginUser() {
    const input = document.getElementById("user-id");
    const userId = input.value.trim();

    if (!userId) {
        alert("Please enter your traveller ID.");
        input.focus();
        return;
    }

    try {
        const data = await apiRequest("/api/user/create", {
            method: "POST",
            body: JSON.stringify({
                user_id: userId
            })
        });

        currentUser = data.user_id;
        savedTravelPreferences = null;

        document.getElementById("username").textContent =
            currentUser;

        document.getElementById("login-section")
            .classList.add("hidden");

        document.getElementById("dashboard-section")
            .classList.remove("hidden");

        favouriteIds.clear();
        latestRecommendations = [];
        allDestinations = [];

        if (data.preferences) {
            populatePreferences(data.preferences);
            savedTravelPreferences = {...data.preferences};
        }

        switchTab("recommendations");

        await Promise.all([
            loadPreferences(),
            loadFavouriteIds(),
            loadAllDestinations(),
            loadDestinationRatings()
        ]);

    } catch (error) {
        alert("Login failed: " + error.message);
    }
}

function logout() {
    currentUser = null;
    savedTravelPreferences = null;
    favouriteIds.clear();
    latestRecommendations = [];
    allDestinations = [];
    document.getElementById("review-modal")?.classList.add("hidden");
    setFestivalMode(false);

    document.getElementById("login-section")
        .classList.remove("hidden");

    document.getElementById("dashboard-section")
        .classList.add("hidden");

    document.getElementById("user-id").value = "";

    [
        "recommendations-list",
        "favourites-list",
        "history-list",
        "all-destinations-list"
    ].forEach(id => {
        const element = document.getElementById(id);

        if (element) {
            element.innerHTML = "";
        }
    });

    showMessage("recommendation-status", "");
    showMessage("preferences-status", "");
}

/* DASHBOARD NAVIGATION */

function switchTab(tabName) {
    const tab = document.getElementById(tabName + "-tab");

    if (!tab) return;

    // Festival Deal page cannot appear in Normal Mode.
    if (tabName === "festival" && !festivalMode) return;
    const backBar = document.getElementById("festival-back-bar");
    backBar?.classList.toggle("hidden", !(festivalMode && tabName === "destinations" && focusedFestivalDestinationId));
    if (tabName !== "destinations") focusedFestivalDestinationId = null;

    document.querySelectorAll(".tab-content").forEach(item => {
        item.classList.remove("active");
        item.classList.add("hidden");
    });

    document.querySelectorAll(".tab-button").forEach(button => {
        button.classList.remove("active");
    });

    tab.classList.remove("hidden");
    tab.classList.add("active");

    const navigationId = festivalMode ? "festival-navigation" : "normal-navigation";
    const selectedButton = document.querySelector(
        `#${navigationId} .tab-button[data-tab="${tabName}"]`
    );

    if (selectedButton) {
        selectedButton.classList.add("active");
    }

    if (!currentUser) return;

    if (tabName === "destinations" || tabName === "festival") syncTripInputsFromPreferences();
    if (tabName === "ratings-reviews") {
        loadAllRatingsAndReviews();
    }
    if (tabName === "preferences") {
        loadPreferences();
    } else if (tabName === "favourites") {
        loadFavourites();
    } else if (tabName === "history") {
        loadHistory();
    } else if (tabName === "destinations") {
        updateExploreFestivalHeader();
        loadAllDestinations();
    }
}

/* SMART DESTINATION AVAILABILITY
 * Uses the same category rules and full-trip budget formula as the Python recommender.
 * Activities are soft preferences in recommendations, so they are only disabled when
 * no affordable category/region destination can possibly offer that activity.
 */
const SMART_CATEGORY_RULES = {
    beach: {activities:["beach"]},
    nature: {activities:["nature", "wildlife", "hiking"], styles:["nature"]},
    city: {styles:["city"]},
    historical: {activities:["history"]},
    adventure: {activities:["adventure", "hiking", "diving", "island_hopping"], styles:["adventure"]}
};
function smartNormalise(value) {
    return String(value ?? "").trim().toLowerCase().replaceAll(" ", "_").replaceAll("-", "_");
}
function smartMatchesCategory(destination, value) {
    const key = smartNormalise(value);
    if (!key || key === "any") return true;
    const rule = SMART_CATEGORY_RULES[key];
    if (!rule) return true;
    const activities = (destination.activities || []).map(smartNormalise);
    const styles = (destination.travel_styles || []).map(smartNormalise);
    return (rule.activities || []).some(a => activities.includes(a)) ||
           (rule.styles || []).some(s => styles.includes(s));
}
function smartPrice(destination, days) {
    const daily = Number(destination.estimated_daily_budget_rm);
    const rate = festivalMode ? getFestivalDiscount(destination.id) : 0;
    return daily * days * (1 - rate / 100);
}
function updateSmartAvailability() {
    const counter = document.getElementById("smart-match-counter");
    const guide = document.getElementById("smart-budget-guide");
    const tip = document.getElementById("smart-selection-tip");
    const category = document.getElementById("category-select");
    const activitiesBox = document.getElementById("activities-options");
    if (!counter || !guide || !category || !activitiesBox) return;
    if (!allDestinations.length) {
        counter.textContent = "Loading destinations…";
        return;
    }
    const budget = Number(document.getElementById("budget-input")?.value);
    const days = Number(document.getElementById("duration-input")?.value);
    if (!Number.isFinite(budget) || budget <= 0 || !Number.isInteger(days) || days < 1 || days > 14) {
        counter.textContent = "Enter a valid budget and duration";
        guide.textContent = "Enter a positive budget and 1–14 days to check availability.";
        return;
    }
    const region = smartNormalise(document.getElementById("region-select")?.value);
    const regionMatches = d => region === "any" || !region || smartNormalise(d.region) === region;
    const available = allDestinations.filter(d => regionMatches(d) && smartPrice(d, days) <= budget);
    // Evaluate each category independently, and keep the Any option enabled.
    const selectedCategory = category.value;
    Array.from(category.options).forEach(option => {
        if (smartNormalise(option.value) === "any") { option.disabled = false; return; }
        const matching = available.filter(d => smartMatchesCategory(d, option.value));
        option.disabled = matching.length === 0;
        const matchingRegion = allDestinations.filter(d => regionMatches(d) && smartMatchesCategory(d, option.value));
        const minimum = matchingRegion.length ? Math.ceil(Math.min(...matchingRegion.map(d => smartPrice(d, days)))) : null;
        option.title = option.disabled ? (minimum === null ? "Not available in this region" : `Requires at least ${formatMoney(minimum)} for ${days} days`) : `${matching.length} affordable destinations`;
        // Do not rewrite the label, so switching the budget back has no display artifacts.
    });
    let resetCategory = false;
    if (category.selectedOptions[0]?.disabled) {
        category.value = "Any";
        resetCategory = true;
    }
    const eligible = available.filter(d => smartMatchesCategory(d, category.value));
    // Recommendations treat activities as matching signals rather than strict filters.
    // Here, dim only activities that have no suitable affordable destination.
    activitiesBox.querySelectorAll('input[type="checkbox"]').forEach(input => {
        const count = eligible.filter(d => (d.activities || []).map(smartNormalise).includes(smartNormalise(input.value))).length;
        input.disabled = count === 0;
        if (input.disabled) input.checked = false;
        const label = input.closest("label");
        label?.classList.toggle("smart-unavailable", input.disabled);
        if (label) label.title = input.disabled ? "No affordable destination offers this activity with the selected category and region" : `${count} affordable destinations offer this activity`;
    });
    counter.textContent = `${eligible.length} affordable destination${eligible.length === 1 ? "" : "s"}`;
    guide.textContent = `Your ${days}-day trip allows up to ${formatMoney(budget / days)} per day.` + (festivalMode ? " Festival discounts are included." : "");
    if (tip) tip.textContent = resetCategory ? "Your previous category is unavailable for this budget. Changed to Any Category."
        : eligible.length === 0 ? "No affordable destination is available. Increase your budget, shorten your trip, or change your region."
        : "Unavailable choices are dimmed. These availability counts are cost-and-category matches, not final AI recommendation scores.";
}

function getFormPreferences() {
    const checkedActivities = [
        ...document.querySelectorAll(
            '#activities-options input[type="checkbox"]:checked'
        )
    ].map(input => input.value);

    return {
        budget_rm: Number(
            document.getElementById("budget-input").value
        ),

        duration_days: Number(
            document.getElementById("duration-input").value
        ),

        destination_category:
            document.getElementById("category-select").value,

        activities: checkedActivities,

        travel_style:
            document.getElementById("style-select").value,

        companion:
            document.getElementById("companion-select").value,

        region:
            document.getElementById("region-select").value
    };
}

function validatePreferences(preferences) {
    if (!Number.isInteger(preferences.budget_rm) ||
        preferences.budget_rm <= 0) {
        return "Please enter a valid budget greater than RM 0.";
    }

    if (!Number.isInteger(preferences.duration_days) ||
        preferences.duration_days < 1 ||
        preferences.duration_days > 14) {
        return "Please enter a trip duration between 1 and 14 days.";
    }

    return null;
}

function populatePreferences(preferences) {
    const fields = {
        "budget-input": preferences.budget_rm,
        "duration-input": preferences.duration_days,
        "category-select": preferences.destination_category,
        "style-select": preferences.travel_style,
        "companion-select": preferences.companion,
        "region-select": preferences.region
    };

    Object.entries(fields).forEach(([id, value]) => {
        const element = document.getElementById(id);

        if (element && value !== undefined && value !== null) {
            element.value = value;
        }
    });

    const selectedActivities = new Set(
        preferences.activities || []
    );

    document.querySelectorAll(
        '#activities-options input[type="checkbox"]'
    ).forEach(checkbox => {
        checkbox.checked = selectedActivities.has(checkbox.value);
    });
}

async function loadPreferences() {
    if (!currentUser) return;

    try {
        const preferences = await apiRequest(
            "/api/user/preferences"
        );

        populatePreferences(preferences);
        savedTravelPreferences = {...preferences};
        syncTripInputsFromPreferences();
        updateSmartAvailability();

    } catch (error) {
        showMessage(
            "preferences-status",
            "Unable to load preferences: " + error.message,
            true
        );
    }
}

async function savePreferences() {
    if (!currentUser) return;

    const preferences = getFormPreferences();
    const validationError = validatePreferences(preferences);

    if (validationError) {
        showMessage(
            "preferences-status",
            validationError,
            true
        );
        return;
    }

    try {
        await apiRequest("/api/user/preferences", {
            method: "POST",
            body: JSON.stringify(preferences)
        });

        savedTravelPreferences = {...preferences};
        syncTripInputsFromPreferences();
        updateSmartAvailability();
        showMessage(
            "preferences-status",
            "Your travel preferences have been saved successfully!"
        );

    } catch (error) {
        showMessage(
            "preferences-status",
            error.message,
            true
        );
    }
}

/* AI TRAVEL RECOMMENDATIONS */

async function generateRecommendations() {
    const container = document.getElementById(
        "recommendations-list"
    );

    const preferences = savedTravelPreferences || getFormPreferences();
    const validationError = validatePreferences(preferences);

    if (validationError) {
        showMessage(
            "recommendation-status",
            validationError,
            true
        );
        return;
    }

    showLoading(container);

    showMessage(
        "recommendation-status",
        "Our rule-based AI is finding destinations for you..."
    );

    try {
        const data = await apiRequest(
            "/api/travel/recommendations",
            {
                method: "POST",
                body: JSON.stringify({
                    ...preferences,
                    festival_mode: festivalMode,
                    festival_id: festivalMode ? selectedFestivalId : null
                })
            }
        );

        latestRecommendations = data.recommendations || [];

        showMessage(
            "recommendation-status",
            `Found ${data.count} destination recommendation(s) ` +
            "based on your travel preferences."
        );

        renderDestinationCards(
            container,
            latestRecommendations,
            true
        );

    } catch (error) {
        showMessage(
            "recommendation-status",
            "Recommendation failed: " + error.message,
            true
        );

        showEmpty(
            container,
            "Unable to generate recommendations."
        );
    }
}

/* DESTINATION CARDS */


function formatMoney(value) {
    if (value === null || value === undefined || value === "") {
        return "Not available";
    }

    const amount = Number(value);

    if (!Number.isFinite(amount)) {
        return "Not available";
    }

    const isWholeNumber = Number.isInteger(amount);

    return "RM " + amount.toLocaleString("en-MY", {
        minimumFractionDigits: isWholeNumber ? 0 : 2,
        maximumFractionDigits: 2
    });
}



/* DESTINATION CARDS */

function createDestinationCard(item, isRecommendation = false) {
    const destination = item.destination || item;

    const card = document.createElement("div");
    card.className = "destination-card";

    /* DESTINATION IMAGE */

   /* DESTINATION IMAGE MAPPING */

const imageFiles = window.DESTINATION_IMAGES || {};

    const imageFile = imageFiles[destination.id];

/* DESTINATION IMAGE DISPLAY */
/* DESTINATION PHOTO GALLERY */

const imageList = Array.isArray(imageFile)
    ? imageFile.slice(0, 10)
    : imageFile
        ? [imageFile]
        : [];

const imageHTML = imageList.length ? `
    <div class="destination-gallery" data-photo-index="0">

        <div class="gallery-images">
            ${imageList.map((filename, index) => `
                <img
                    src="/static/images/${encodeURIComponent(filename)}"
                    alt="${escapeHTML(destination.name)} - Photo ${index + 1}"
                    class="destination-image ${index === 0 ? "active" : ""}"
                    loading="lazy"
                >
            `).join("")}
        </div>

        ${imageList.length > 1 ? `
            <button
                type="button"
                class="gallery-arrow gallery-prev"
                aria-label="Previous photo">
                &#10094;
            </button>

            <button
                type="button"
                class="gallery-arrow gallery-next"
                aria-label="Next photo">
                &#10095;
            </button>

            <div class="gallery-counter">
                1 / ${imageList.length}
            </div>
        ` : ""}

    </div>
` : "";


    const score = item.score;
    const totalCost = item.estimated_total_rm;
    const days = item.suggested_days;

    const activities = Array.isArray(destination.activities)
        ? destination.activities
        : [];

    const highlights = Array.isArray(destination.highlights)
        ? destination.highlights
        : [];

    const reasons = Array.isArray(item.reasons)
        ? item.reasons
        : [];

    const warnings = Array.isArray(item.warnings)
        ? item.warnings
        : [];

    const saved = favouriteIds.has(destination.id);

    const tagsHTML = activities.slice(0, 5).map(activity =>
        `<span class="tag">${escapeHTML(
            activity.replaceAll("_", " ")
        )}</span>`
    ).join("");

    const highlightsHTML = highlights.length ? `
        <div class="destination-highlights">
            <h4>Top Attractions</h4>
            <ul>
                ${highlights.map(place =>
                    `<li>${escapeHTML(place)}</li>`
                ).join("")}
            </ul>
        </div>
    ` : "";

    


const scoreHTML = isRecommendation ? `
    <span class="match-score"
          ${!festivalMode ? `
          style="
              background: #e0f5e9 !important;
              color: #00875a !important;
              border: 1px solid #b8dfc9 !important;
              border-radius: 25px !important;
              box-shadow: none !important;
              outline: none !important;
          "` : ""}>
        ${escapeHTML(Number(score).toFixed(1))}% Match
    </span>
` : "";


const inlineRatingHTML = `
    <span class="destination-rating-inline"
          data-rating-id="${escapeHTML(destination.id)}">
        <span class="rating-star">★</span>
        <span class="rating-empty">No ratings yet</span>
    </span>
`;

    /* SECTION: FULL-TRIP PRICE; NORMAL OR FESTIVAL MODE */
    const discount = festivalMode ? getFestivalDiscount(destination.id) : 0;
    const tripDays = isRecommendation ? Number(item.suggested_days) : getTripSettings("explore").days;
    const baseAmount = isRecommendation
        ? Number(item.original_total_rm ?? totalCost)
        : Number(destination.estimated_daily_budget_rm) * tripDays;
    const discountedAmount = isRecommendation && Number(item.discount_percent) === discount && discount > 0
        ? Number(totalCost)
        : Math.round(baseAmount * (1 - discount / 100) * 100) / 100;
    const priceHTML = discount > 0 ? `
        <span class="discount-price-line">
            <span class="price-original">${escapeHTML(formatMoney(baseAmount))}</span>
            <span class="price-discounted">${escapeHTML(formatMoney(discountedAmount))}</span>
            <span class="discount-badge">${discount}% OFF</span>
        </span>
        
        <span class="festival-price-details">
            <span class="price-caption">
                ${tripDays}-day total · Save ${escapeHTML(formatMoney(baseAmount-discountedAmount))}
            </span>
            ${festivalMode && !isRecommendation ? inlineRatingHTML : ""}
        </span>

    ` : `${escapeHTML(formatMoney(baseAmount))}<span class="price-caption">${tripDays}-day estimated total</span>`;

    
const reasonsHTML = isRecommendation && reasons.length
    ? `
        <div class="recommendation-reasons">
            <strong>Why is this destination recommended ?</strong>
            <ul>
                ${reasons.map(reason =>
                    `<li>${escapeHTML(reason)}</li>`
                ).join("")}
            </ul>
        </div>
    `
    : "";


    const warningsHTML = warnings.length ? `
        <div class="recommendation-reasons">
            <strong>Travel considerations:</strong>
            <ul>
                ${warnings.map(warning =>
                    `<li>${escapeHTML(warning)}</li>`
                ).join("")}
            </ul>
        </div>
    ` : "";

    card.innerHTML = `
    ${imageHTML}

    <div class="destination-content">

            <h3>${escapeHTML(destination.name)}</h3>

            <div class="destination-state">
                📍 ${escapeHTML(destination.state)}
                · ${escapeHTML(destination.region)}
            </div>

            <p class="destination-description">
                ${escapeHTML(destination.description || "")}
            </p>

            <div class="destination-tags">
                ${tagsHTML}
            </div>

            ${highlightsHTML}

            
            
            <div class="destination-meta">
                <div class="destination-meta-left">
                ${scoreHTML}
                ${festivalMode && !isRecommendation ? "" : inlineRatingHTML}
            </div>

                <span class="destination-price">
                    ${priceHTML}
                </span>
            </div>


            <p class="destination-duration">
                🗓️ ${
                    isRecommendation
                        ? escapeHTML(days) + " suggested day(s)"
                        : escapeHTML(tripDays) + " selected day(s) · " + escapeHTML(
                            destination.recommended_days_min
                        ) + "–" + escapeHTML(
                            destination.recommended_days_max
                        ) + " usual recommended day(s)"
                }
            </p>

            ${reasonsHTML}
            ${warningsHTML}

            <div class="destination-actions">
                <button
                    type="button"
                    class="btn-favourite ${saved ? "saved" : ""}"
                    data-destination-id="${escapeHTML(destination.id)}"
                >
                    ${saved ? "♥ Saved" : "♡ Add to Favourites"}
                </button>
            </div>

        </div>
    `;

    // Ratings and reviews are available in normal and festival mode.
    const actions = card.querySelector(".destination-actions");
    if (actions) {
        const reviewButton = document.createElement("button");
        reviewButton.type = "button";
        reviewButton.className = "btn-review";
        reviewButton.dataset.reviewId = destination.id;
        reviewButton.dataset.reviewName = destination.name;
        reviewButton.textContent = "⭐ Rate Destination";
        actions.appendChild(reviewButton);
       
    }
    updateDestinationRatingDisplaysForCard(card);
    return card;
}


function renderDestinationCards(
    container,
    destinations,
    isRecommendation = false
) {
    if (!container) return;

    container.innerHTML = "";

    if (!destinations.length) {
        showEmpty(
            container,
            isRecommendation
                ? `No matching trip found within ${formatMoney(getFormPreferences().budget_rm)} for ${getFormPreferences().duration_days} selected days. Try a higher budget, shorter stay, or different interests.`
                : "No destinations match your search, selected duration and budget filters. Try broadening the search or clearing the budget filter."
        );
        return;
    }

    destinations.forEach(item => {
        container.appendChild(
            createDestinationCard(item, isRecommendation)
        );
    });
}

/* FAVOURITES */

async function loadFavouriteIds() {
    if (!currentUser) return;

    try {
        const destinations = await apiRequest(
            "/api/user/favourites"
        );

        favouriteIds = new Set(
            destinations.map(destination => destination.id)
        );

        updateFavouriteButtons();

    } catch (error) {
        console.error("Unable to load favourites:", error);
    }
}

async function loadFavourites() {
    const container = document.getElementById(
        "favourites-list"
    );

    if (!currentUser) return;

    showLoading(container);

    try {
        const destinations = await apiRequest(
            "/api/user/favourites"
        );

        favouriteIds = new Set(
            destinations.map(destination => destination.id)
        );

        renderDestinationCards(container, destinations);
        updateFavouriteButtons();

    } catch (error) {
        showEmpty(
            container,
            "Unable to load favourites: " + error.message
        );
    }
}

async function handleFavouriteClick(event) {
    const button = event.target.closest(
        "[data-destination-id]"
    );

    if (!button) return;

    if (!currentUser) {
        alert("Please log in to save favourite destinations.");
        return;
    }

    const destinationId = button.dataset.destinationId;
    const alreadySaved = favouriteIds.has(destinationId);

    button.disabled = true;

    try {
        const data = await apiRequest(
            "/api/user/favourites",
            {
                method: alreadySaved ? "DELETE" : "POST",
                body: JSON.stringify({
                    destination_id: destinationId
                })
            }
        );

        favouriteIds = new Set(
            data.favourite_destination_ids || []
        );

        updateFavouriteButtons();

        const favouritesTab = document.getElementById(
            "favourites-tab"
        );

        if (favouritesTab?.classList.contains("active")) {
            await loadFavourites();
        }

    } catch (error) {
        alert("Unable to update favourites: " + error.message);
    } finally {
        button.disabled = false;
    }
}

function updateFavouriteButtons() {
    document.querySelectorAll(
        "[data-destination-id]"
    ).forEach(button => {
        const saved = favouriteIds.has(
            button.dataset.destinationId
        );

        button.classList.toggle("saved", saved);

        button.textContent = saved
            ? "♥ Saved"
            : "♡ Add to Favourites";
    });
}

/* RECOMMENDATION HISTORY */

async function loadHistory() {
    const container = document.getElementById("history-list");

    if (!container) return;

    showLoading(container);

    try {
        const history = await apiRequest("/api/user/history");

        if (allDestinations.length === 0) {
            allDestinations = await apiRequest(
                "/api/travel/destinations"
            );
        }

        container.innerHTML = "";

        if (!Array.isArray(history) || history.length === 0) {
            showEmpty(
                container,
                "No recommendation history found."
            );
            return;
        }

        const sortedHistory = [...history].sort(
            (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
        );

        sortedHistory.forEach((entry, index) => {
            const item = document.createElement("div");
            item.className = "history-item";

            const preferences = entry.preferences || {};
            const destinationIds = entry.destination_ids || [];

            const date = new Date(entry.timestamp);

            const dateText = Number.isNaN(date.getTime())
                ? "Date unavailable"
                : date.toLocaleString("en-MY");

            const destinationNames = destinationIds.map(id => {
                const destination = allDestinations.find(
                    d => d.id === id
                );

                return destination ? destination.name : id;
            });

            item.innerHTML = `
                <h4>
                    Travel Recommendation #${sortedHistory.length - index}
                </h4>

                <p>🕒 ${escapeHTML(dateText)}</p>

                <p>
                    <strong>Budget:</strong>
                    ${escapeHTML(formatMoney(preferences.budget_rm))}
                </p>

                <p>
                    <strong>Duration:</strong>
                    ${escapeHTML(preferences.duration_days)} days
                </p>

                <p>
                    <strong>Category:</strong>
                    ${escapeHTML(preferences.destination_category)}
                </p>

                <p>
                    <strong>Activities:</strong>
                    ${escapeHTML(
                        (preferences.activities || []).join(", ") || "Any"
                    )}
                </p>

                <p>
                    <strong>Travel Style:</strong>
                    ${escapeHTML(preferences.travel_style)}
                </p>

                <p>
                    <strong>Recommended Destinations:</strong>
                </p>

                <ul style="padding-left: 20px; margin-top: 8px;">
                    ${destinationNames.map(name =>
                        `<li>${escapeHTML(name)}</li>`
                    ).join("")}
                </ul>
            `;

            container.appendChild(item);
        });

    } catch (error) {
        console.error("History error:", error);

        showEmpty(
            container,
            "Unable to load recommendation history: " + error.message
        );
    }
}

/* ALL MALAYSIAN DESTINATIONS */

async function loadAllDestinations() {
    const container = document.getElementById(
        "all-destinations-list"
    );

    if (!container) return;

    showLoading(container);

    try {
        allDestinations = await apiRequest(
            "/api/travel/destinations"
        );

        populateStateFilter();
        updateExploreLocationOptions();
        updateSmartAvailability();
        filterDestinations();
        renderFestivalDeals();

    } catch (error) {
        showEmpty(
            container,
            "Unable to load destinations: " + error.message
        );
    }
}

/* DESTINATION SEARCH AND FILTERS */

function populateStateFilter() {
    const stateSelect = document.getElementById("state-filter");

    if (!stateSelect) return;

    const selectedState = stateSelect.value;

    const states = [...new Set(
        allDestinations.map(destination => destination.state)
    )].sort();

    stateSelect.innerHTML =
        '<option value="Any">All States</option>';

    states.forEach(state => {
        const option = document.createElement("option");

        option.value = state;
        option.textContent = state;

        stateSelect.appendChild(option);
    });

    if (states.includes(selectedState)) {
        stateSelect.value = selectedState;
    }
    updateExploreLocationOptions();
}


/* SMART STATE + REGION FILTERS
 * Build the map from real destination records to avoid hard-coded assumptions.
 * State selection automatically selects the correct region.
 * Region selection disables incompatible states and clears an invalid state.
 * Search text never locks a state; users can still change their search.
 */
function exploreStateRegionMap() {
    const mapping = new Map();
    allDestinations.forEach(destination => {
        const state = String(destination.state || "").trim();
        const region = String(destination.region || "").trim();
        if (state && region) mapping.set(state, region);
    });
    return mapping;
}

function updateExploreLocationOptions() {
    const stateSelect = document.getElementById("state-filter");
    const regionSelect = document.getElementById("region-filter");
    if (!stateSelect || !regionSelect) return;

    const selectedRegion = regionSelect.value;
    const regionsByState = exploreStateRegionMap();
    Array.from(stateSelect.options).forEach(option => {
        if (option.value === "Any") {
            option.disabled = false;
            option.title = "Show destinations in all states";
            return;
        }
        const actualRegion = regionsByState.get(option.value);
        const incompatible = selectedRegion !== "Any" && actualRegion !== selectedRegion;
        option.disabled = incompatible;
        option.title = incompatible
            ? `Located in ${actualRegion || "another region"}; choose that region to select this state`
            : `Located in ${actualRegion || "Malaysia"}`;
    });
    // Never leave a disabled option selected.
    const activeOption = stateSelect.selectedOptions[0];
    if (activeOption?.disabled) stateSelect.value = "Any";
}

function handleExploreRegionChange() {
    const stateSelect = document.getElementById("state-filter");
    const regionSelect = document.getElementById("region-filter");
    if (stateSelect && regionSelect && stateSelect.value !== "Any") {
        const correctRegion = exploreStateRegionMap().get(stateSelect.value);
        if (regionSelect.value !== "Any" && correctRegion !== regionSelect.value) {
            stateSelect.value = "Any";
        }
    }
    updateExploreLocationOptions();
    filterDestinations();
}

function handleExploreStateChange() {
    const stateSelect = document.getElementById("state-filter");
    const regionSelect = document.getElementById("region-filter");
    if (stateSelect && regionSelect && stateSelect.value !== "Any") {
        const actualRegion = exploreStateRegionMap().get(stateSelect.value);
        if (actualRegion && Array.from(regionSelect.options).some(o => o.value === actualRegion)) {
            regionSelect.value = actualRegion;
        }
    }
    updateExploreLocationOptions();
    filterDestinations();
}

/* SECTION: EXPLORE FESTIVAL MODE PRESENTATION */
function updateExploreFestivalHeader() {
    const heading = document.getElementById("explore-heading");
    const description = document.getElementById("explore-description");
    const context = document.getElementById("explore-festival-context");
    const name = document.getElementById("explore-festival-name");
    if (!heading || !description || !context) return;
    heading.textContent = festivalMode ? "🎉 Explore Festival Destinations" : "Explore Malaysia";
    description.textContent = festivalMode
        ? "Search and filter Malaysian destinations with festival-adjusted trip prices."
        : "Discover beautiful destinations across Malaysia. Search and filter places based on your interests.";
    context.classList.toggle("hidden", !festivalMode);
    if (name) name.textContent = (activeFestival()?.name || "Festival") + " Travel Offers";
}

/* DESTINATION SEARCH AND FILTERS */

function filterDestinations() {
    const searchText = document.getElementById(
        "destination-search"
    )?.value.trim().toLowerCase() || "";

    const selectedState = document.getElementById(
        "state-filter"
    )?.value || "Any";

    const selectedRegion = document.getElementById(
        "region-filter"
    )?.value || "Any";

    const trip = getTripSettings("explore");
    const withinBudgetOnly = document.getElementById("explore-affordable")?.checked || false;
    const filteredDestinations = allDestinations.filter(destination => {
        if (festivalMode && focusedFestivalDestinationId &&
            destination.id !== focusedFestivalDestinationId) return false;

        // Allow searching by name, state, region, activities and attractions
        const searchableText = [
            destination.name,
            destination.state,
            destination.region,
            destination.description,
            ...(destination.activities || []),
            ...(destination.highlights || [])
        ]
        .filter(Boolean)
        .join(" ")
        .replaceAll("_", " ")
        .toLowerCase();

        const matchesSearch = searchableText.includes(searchText);

        const matchesState =
            selectedState === "Any" ||
            destination.state === selectedState;

        const matchesRegion =
            selectedRegion === "Any" ||
            destination.region === selectedRegion;

        const estimatedTotal = Number(destination.estimated_daily_budget_rm) * trip.days *
            (1 - (festivalMode ? getFestivalDiscount(destination.id) : 0) / 100);
        const matchesBudget = !withinBudgetOnly || estimatedTotal <= trip.budget;
        return matchesSearch && matchesState && matchesRegion && matchesBudget;
    });

    renderDestinationCards(
        document.getElementById("all-destinations-list"),
        filteredDestinations
    );

    const countElement = document.getElementById(
        "destination-results-count"
    );

    if (countElement) {
        countElement.textContent =
            `Showing ${filteredDestinations.length} of ` +
            `${allDestinations.length} destinations · ${trip.days}-day trip` +
            (festivalMode ? ` · ${activeFestival()?.name || "Festival"} prices` : " · Standard prices") +
            (withinBudgetOnly ? ` · Budget up to ${formatMoney(trip.budget)}` : "");
    }
}


function clearDestinationFilters() {
    const searchInput = document.getElementById(
        "destination-search"
    );

    const stateSelect = document.getElementById(
        "state-filter"
    );

    const regionSelect = document.getElementById(
        "region-filter"
    );

    focusedFestivalDestinationId = null;
    document.getElementById("festival-back-bar")?.classList.add("hidden");
    if (searchInput) {
        searchInput.value = "";
    }

    if (stateSelect) {
        stateSelect.value = "Any";
    }

    if (regionSelect) {
        regionSelect.value = "Any";
    }

    updateExploreLocationOptions();
    filterDestinations();
}

/* DESTINATION GALLERY NAVIGATION */

document.addEventListener("click", function (event) {
    const button = event.target.closest(
        ".gallery-prev, .gallery-next"
    );

    if (!button) return;

    event.preventDefault();

    const gallery = button.closest(".destination-gallery");
    if (!gallery) return;

    const images = gallery.querySelectorAll(
        ".gallery-images img.destination-image"
    );

    if (images.length < 2) return;

    let index = Number(gallery.dataset.photoIndex) || 0;

    index = button.classList.contains("gallery-next")
        ? (index + 1) % images.length
        : (index - 1 + images.length) % images.length;

    images.forEach((image, i) => {
        image.classList.toggle("active", i === index);
    });

    gallery.dataset.photoIndex = String(index);

    const counter = gallery.querySelector(".gallery-counter");

    if (counter) {
        counter.textContent = `${index + 1} / ${images.length}`;
    }
});

/* SECTION: FESTIVAL PROMOTIONS */
async function loadFestivalPromotions() {
    try {
        const data = await apiRequest("/api/travel/festivals");
        festivalOffers = data.festivals || [];
        const select = document.getElementById("festival-select");
        if (!select) return;
        select.innerHTML = festivalOffers.map(f =>
            `<option value="${escapeHTML(f.id)}">${escapeHTML(f.name)}</option>`
        ).join("");
        if (!festivalOffers.some(f => f.id === selectedFestivalId)) {
            selectedFestivalId = festivalOffers[0]?.id || "";
        }
        select.value = selectedFestivalId;
        updateFestivalColourTheme();
        updateExploreFestivalHeader();
        updateSmartAvailability();
        renderFestivalDeals();
    } catch (error) {
        showMessage("festival-status", "Unable to load festival data: " + error.message, true);
    }
}

function activeFestival() {
    return festivalOffers.find(f => f.id === selectedFestivalId) || null;
}

function getFestivalDiscount(destinationId) {
    const discount = Number(activeFestival()?.offers?.[destinationId] || 0);
    return Number.isFinite(discount) && discount > 0 && discount <= 70 ? discount : 0;
}

function setFestivalMode(enabled) {
    festivalMode = Boolean(enabled);
    focusedFestivalDestinationId = null;
    document.body.classList.toggle("festival-mode", festivalMode);
    updateFestivalColourTheme();
    updateExploreFestivalHeader();
    updateSmartAvailability();
    document.getElementById("festival-mode-button")?.classList.toggle("hidden", festivalMode);
    document.getElementById("exit-festival-button")?.classList.toggle("hidden", !festivalMode);
    document.getElementById("festival-banner")?.classList.toggle("hidden", !festivalMode);
    document.getElementById("festival-navigation")?.classList.toggle("hidden", !festivalMode);
    document.getElementById("festival-back-bar")?.classList.add("hidden");
    document.getElementById("destination-search").value = "";
    document.getElementById("state-filter").value = "Any";
    document.getElementById("region-filter").value = "Any";
    updateExploreLocationOptions();
    if (festivalMode) {
        renderFestivalDeals();
        switchTab("festival");
    } else {
        switchTab("recommendations");
    }
    refreshFestivalPrices();
    window.scrollTo({top: 0, behavior: "smooth"});
}

function refreshFestivalPrices() {
    if (!currentUser) return;
    if (allDestinations.length) filterDestinations();
    if (latestRecommendations.length) {
        // When a mode changes, remove stale recommendation results instead of displaying
        // potentially incorrect budget-eligibility calculations.
        latestRecommendations = [];
        const container = document.getElementById("recommendations-list");
        showEmpty(container, "Click Find My Destinations to calculate recommendations for the selected mode.");
        showMessage("recommendation-status", "Mode changed. Generate recommendations to apply its budget rules.");
    }
    if (document.getElementById("favourites-tab")?.classList.contains("active")) loadFavourites();
}

/* SECTION: SHARED TRIP PLANNING AND FESTIVAL DEALS */
function getTripSettings() {
    // Never read separate values from Explore or Festival Mode.
    // These pages always use the user's last saved Travel Preferences.
    const p = savedTravelPreferences || getFormPreferences();
    const d = Number(p.duration_days);
    const b = Number(p.budget_rm);
    return {
        days: Number.isInteger(d) && d >= 1 && d <= 14 ? d : 3,
        budget: Number.isFinite(b) && b > 0 ? b : 800
    };
}

function syncTripInputsFromPreferences() {
    const {days, budget} = getTripSettings();
    const category = savedTravelPreferences?.destination_category || "Any";
    const safeCategory = escapeHTML(category === "Any" ? "Any Category" : category);
    const summary = `<span class="trip-summary-chip">💰 ${escapeHTML(formatMoney(budget))} Budget</span>` +
        `<span class="trip-summary-chip">📅 ${days} Days</span>` +
        `<span class="trip-summary-chip">🌴 ${safeCategory}</span>` +
        `<a class="edit-preferences-link" href="#" data-edit-preferences>Edit Travel Preferences →</a>`;
    ["festival-trip-summary", "recommendation-trip-summary"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = summary;
    });
    if (allDestinations.length) filterDestinations();
    renderFestivalDeals();
}

document.addEventListener("click", event => {
    const link = event.target.closest("[data-edit-preferences]");
    if (!link) return;
    event.preventDefault();
    switchTab("preferences");
});

function renderFestivalDeals() {
    const container = document.getElementById("festival-deals-list");
    if (!container) return;
    container.replaceChildren();
    const festival = activeFestival();
    if (!festival) {
        showEmpty(container, "Festival offers are unavailable. Restart Flask and check festival_promotions.json.");
        return;
    }
    const {days, budget} = getTripSettings("festival");
    const affordableOnly = document.getElementById("festival-affordable")?.checked || false;
    const sortBy = document.getElementById("festival-sort")?.value || "biggest";
    const deals = allDestinations
        .filter(d => getFestivalDiscount(d.id) > 0)
        .map(d => {
            const percent = getFestivalDiscount(d.id);
            const original = Math.round(Number(d.estimated_daily_budget_rm) * days * 100) / 100;
            const discounted = Math.round(original * (1-percent/100) * 100) / 100;
            return {destination:d, percent, original, discounted, savings:original-discounted};
        })
        .filter(x => !affordableOnly || x.discounted <= budget)
        .sort((a,b) => sortBy === "lowest" ? a.discounted-b.discounted
                     : sortBy === "savings" ? b.savings-a.savings
                     : sortBy === "name" ? a.destination.name.localeCompare(b.destination.name)
                     : b.percent-a.percent || a.discounted-b.discounted);
    showMessage("festival-status", `${festival.name} · ${deals.length} destinations · ${days}-day trip estimates` +
        (affordableOnly ? ` · Budget up to ${formatMoney(budget)}` : ""));
    if (!deals.length) {
        showEmpty(container, "No destinations match this trip budget and duration. Try increasing your budget, shortening your stay, or turning off the budget filter.");
        return;
    }
    deals.forEach(({destination, percent, original, discounted, savings}) => {
        const imageData = window.DESTINATION_IMAGES?.[destination.id];
        const filename = Array.isArray(imageData) ? imageData[0] : imageData;
        const coverImage = filename ? `<img class="deal-cover" src="/static/images/${encodeURIComponent(filename)}" alt="${escapeHTML(destination.name)}">` : "";
        const card = document.createElement("article");
        card.className = "festival-deal-card";
        card.innerHTML = `
            ${coverImage}
            <div class="deal-content">
                
            <div class="deal-head">
                <h4>
                    ${escapeHTML(destination.name)},
                    ${escapeHTML(destination.state)}
                </h4>
            </div>

            <div class="festival-price">
                <span class="price-original">
                    ${escapeHTML(formatMoney(original))}
                </span>

                <span class="price-discounted">
                    ${escapeHTML(formatMoney(discounted))}
                </span>

                <span class="discount-badge">
                    ${percent}% OFF
                </span>
            </div>

                            <span class="price-caption">${days}-day estimated total · Save ${escapeHTML(formatMoney(savings))}</span>
                            <span class="budget-indicator ${discounted<=budget?'in-budget':'over-budget'}">${discounted<=budget ? '✓ Within your budget':'Above selected budget'}</span>
                            <button type="button" class="btn-view-festival" data-festival-destination="${escapeHTML(destination.id)}">View Destination →</button>
                        </div>`;
                    container.appendChild(card);
                });
            }

async function openFestivalDestination(destinationId) {
    if (!festivalMode) return;
    if (!allDestinations.length) await loadAllDestinations();
    if (!allDestinations.some(d => d.id === destinationId)) return;
    focusedFestivalDestinationId = destinationId;
    // Carry the festival trip context into the same Explore Destinations card.
    // Clear filters so only the selected destination appears.
    document.getElementById("destination-search").value = "";
    document.getElementById("state-filter").value = "Any";
    document.getElementById("region-filter").value = "Any";
    updateExploreLocationOptions();
    switchTab("destinations");
    filterDestinations();
    document.getElementById("festival-back-bar")?.classList.remove("hidden");
    const card = document.querySelector("#all-destinations-list .destination-card");
    card?.classList.add("festival-target");
    document.getElementById("destinations-tab")?.scrollIntoView({behavior:"smooth",block:"start"});
}


/* === TEAMMATE FEATURE: RATINGS AND REVIEWS === */
/* =========================================
   USER RATING AND REVIEW SYSTEM
   ========================================= */


let selectedReviewDestination = null;


// 1. Open the review panel
document.addEventListener("click", async function(event) {


    const button = event.target.closest(".btn-review");


    if (!button) return;


    selectedReviewDestination = button.dataset.reviewId;


    const destinationName = button.dataset.reviewName;


    document.getElementById("review-destination-name")
        .textContent = destinationName;


    document.getElementById("review-modal")
        .classList.remove("hidden");


    document.getElementById("review-form").reset();
    await loadDestinationReviews(selectedReviewDestination);


    document.getElementById("review-message")
        .textContent = "";


});




// 2. Load reviews from the Flask backend
async function loadDestinationReviews(destinationId) {


    const reviewList = document.getElementById("review-list");
    const average = document.getElementById("review-average");


    reviewList.textContent = "Loading reviews...";


    try {


        const data = await apiRequest(
            `/api/travel/destinations/${encodeURIComponent(destinationId)}/reviews`
        );


        if (data.total_reviews > 0) {
            average.textContent =
                `⭐ ${data.average_rating} / 5 (${data.total_reviews} reviews)`;
        } else {
            average.textContent = "No ratings yet";
        }


        reviewList.innerHTML = "";


        if (data.reviews.length === 0) {
            reviewList.textContent =
                "No reviews yet. Be the first to review!";
            return;
        }


        data.reviews.forEach(review => {


            const reviewItem = document.createElement("div");
            reviewItem.className = "review-item";


            const username = document.createElement("strong");
            username.textContent = review.user_id;


            const stars = document.createElement("p");
            stars.textContent =
                "★".repeat(review.rating) +
                "☆".repeat(5 - review.rating);


            const comment = document.createElement("p");
            comment.textContent = review.review;


            reviewItem.appendChild(username);
            reviewItem.appendChild(stars);
            reviewItem.appendChild(comment);


            reviewList.appendChild(reviewItem);
        });


    } catch (error) {


        reviewList.textContent =
            "Unable to load reviews: " + error.message;


        console.error("Review loading error:", error);
    }
}




// 3. Submit a new rating and review
document.getElementById("review-form")
    ?.addEventListener("submit", async function(event) {


        event.preventDefault();


        if (!selectedReviewDestination) return;


        const rating = Number(
            document.getElementById("review-rating").value
        );


        const review = document.getElementById(
            "review-comment"
        ).value.trim();


        const message = document.getElementById("review-message");


       
        /* Rating is required, written review is optional */


        if (!Number.isInteger(rating) ||
            rating < 1 || rating > 5) {


            message.textContent =
                "Please select a rating before submitting.";


            return;
        }




        try {


            await apiRequest(
                `/api/travel/destinations/${encodeURIComponent(selectedReviewDestination)}/reviews`,
                {
                    method: "POST",
                    body: JSON.stringify({
                        rating: rating,
                        review: review
                    })
                }
            );


            message.textContent =
                "Review submitted successfully!";


            document.getElementById("review-form").reset();


           
            await refreshRatingInformation();




        } catch (error) {


            message.textContent =
                "Unable to submit review: " + error.message;


        }
    });




// 4. Close the review panel
document.getElementById("close-review")
    ?.addEventListener("click", function() {


        document.getElementById("review-modal")
            .classList.add("hidden");


        selectedReviewDestination = null;
    });




/* ==========================================
   NEW: DESTINATION AVERAGE RATINGS
   ========================================== */


let destinationRatings = {};
let allRatingsReviewsData = [];


// Retrieve average ratings from Flask
async function loadDestinationRatings() {
    try {
        destinationRatings = await apiRequest(
            "/api/travel/ratings"
        );


        updateDestinationRatingDisplays();


    } catch (error) {
        console.error("Unable to load destination ratings:", error);
    }
}


// Display average rating on destination cards
function updateDestinationRatingDisplays() {
    document.querySelectorAll(".destination-card").forEach(card => {
        updateDestinationRatingDisplaysForCard(card);
    });
}


/* ==========================================
   NEW: RATINGS AND REVIEWS SECTION
   ========================================== */


/* =========================================
   COMPACT PROFESSIONAL RATING DASHBOARD
   ========================================= */

let expandedReviewDestinationIds = new Set();

// Load ratings and reviews from Flask
async function loadAllRatingsAndReviews() {
    const container = document.getElementById(
        "ratings-reviews-list"
    );

    if (!container) return;

    container.innerHTML =
        '<div class="loading">Loading traveller ratings...</div>';

    try {
        const data = await apiRequest("/api/travel/all-reviews");

        allRatingsReviewsData = Array.isArray(data.destinations)
            ? data.destinations
            : [];

        // Use existing destination activities for interest filters
        if (!allDestinations.length) {
            try {
                allDestinations = await apiRequest(
                    "/api/travel/destinations"
                );
            } catch (error) {
                console.warn(
                    "Destination interests unavailable:",
                    error
                );
            }
        }

        populateReviewInterestOptions();
        filterRatingsAndReviews();

    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                Unable to load ratings and reviews:
                ${escapeHTML(error.message)}
            </div>
        `;
    }
}


// Find interests for each destination
function reviewInterestTags(destination) {
    const details = allDestinations.find(
        item => item.id === destination.destination_id
    );

    if (!details) return [];

    const values = [
        ...(Array.isArray(details.activities)
            ? details.activities : []),

        ...(Array.isArray(details.travel_styles)
            ? details.travel_styles : []),

        details.category || "",
        details.destination_category || ""

    ].map(value =>
        String(value)
            .toLowerCase()
            .replace(/[_-]/g, " ")
    );

    const contains = terms =>
        terms.some(term =>
            values.some(value => value.includes(term))
        );

    const tags = [];

    if (contains(["food", "dining", "culinary"])) {
        tags.push("food");
    }

    if (contains(["nature", "wildlife", "hiking", "forest"])) {
        tags.push("nature");
    }

    if (contains(["beach", "island", "diving", "snorkel"])) {
        tags.push("beach");
    }

    if (contains(["adventure", "hiking", "diving", "outdoor"])) {
        tags.push("adventure");
    }

    if (contains(["shopping"])) {
        tags.push("shopping");
    }

    if (contains([
        "history", "historical", "culture", "heritage"
    ])) {
        tags.push("culture");
    }

    if (contains(["relaxation", "wellness", "spa"])) {
        tags.push("relaxation");
    }

    return tags;
}


// Populate interest filter using available destination data
function populateReviewInterestOptions() {
    const select = document.getElementById(
        "reviews-interest-filter"
    );

    if (!select) return;

    const available = new Set(
        allRatingsReviewsData.flatMap(reviewInterestTags)
    );

    const labels = [
        ["all", "All interests"],
        ["food", "Food & Dining"],
        ["nature", "Nature & Wildlife"],
        ["beach", "Beaches & Islands"],
        ["adventure", "Adventure"],
        ["shopping", "Shopping"],
        ["culture", "Culture & History"],
        ["relaxation", "Relaxation"]
    ];

    const selected = select.value || "all";

    select.innerHTML = labels.map(([id, label]) => `
        <option value="${id}"
            ${id !== "all" && !available.has(id)
                ? "disabled" : ""}>
            ${label}
        </option>
    `).join("");

    select.value =
        selected === "all" || available.has(selected)
            ? selected
            : "all";
}


// Create one compact rating dashboard card
function renderReviewDashboardCard(destination) {
    const card = document.createElement("article");

    card.className =
        "ratings-review-card compact-rating-card";

    const reviews = Array.isArray(destination.reviews)
        ? destination.reviews
        : [];

    const average =
        Number(destination.average_rating) || 0;

    const count =
        Number(destination.total_ratings) || reviews.length;

    // Count ratings for each star level
    const byStars = [5, 4, 3, 2, 1].map(stars =>
        reviews.filter(
            review => Number(review.rating) === stars
        ).length
    );

    const percent = number =>
        count ? Math.round(number / count * 100) : 0;

    const tags = reviewInterestTags(destination);

    const labels = {
        food: "Food",
        nature: "Nature",
        beach: "Beaches",
        adventure: "Adventure",
        shopping: "Shopping",
        culture: "Culture",
        relaxation: "Relaxation"
    };

    const expanded = expandedReviewDestinationIds.has(
        destination.destination_id
    );

    // Show one review first, all reviews when expanded
    const preview = expanded
        ? reviews
        : reviews.slice(0, 1);

    const compactReviews = preview.map(review => {
        const stars = Math.max(
            0,
            Math.min(5, Number(review.rating) || 0)
        );

        const reviewText =
            String(review.review || "").trim();

        return `
            <div class="compact-review-item">

                <div class="compact-review-head">
                    <strong>
                        ${escapeHTML(review.user_id || "Traveller")}
                    </strong>

                    <span class="compact-review-stars"
                          aria-label="${stars} out of 5 stars">
                        ${"★".repeat(stars)}
                        ${"☆".repeat(5 - stars)}
                    </span>
                </div>

                ${reviewText
                    ? `<p>${escapeHTML(reviewText)}</p>`
                    : `<p class="review-no-comment">
                           Rating only — no written review
                       </p>`
                }

            </div>
        `;
    }).join("");

    card.innerHTML = `

        <!-- DESTINATION NAME AND OVERALL RATING -->
        <div class="compact-rating-heading">

            <div class="compact-rating-place">
                <h3>
                    ${escapeHTML(destination.destination_name)}
                </h3>

                <p>
                    📍 ${escapeHTML(destination.state)}
                </p>
            </div>

            <div class="compact-rating-score">
                <strong>${average.toFixed(1)}</strong>

                <span class="compact-rating-score-star">
                    ★
                </span>

                <small>
                    ${count}
                    ${count === 1 ? "rating" : "ratings"}
                </small>
            </div>

        </div>

        <!-- DESTINATION INTEREST TAGS -->
        ${tags.length ? `
            <div class="compact-rating-tags">
                ${tags.slice(0, 3).map(tag => `
                    <span>${labels[tag]}</span>
                `).join("")}
            </div>
        ` : ""}

        <!-- FIVE STAR RATING DISTRIBUTION -->
        <div class="compact-rating-distribution"
             aria-label="Rating distribution">

            ${byStars.map((number, index) => `

                <div class="rating-distribution-row">

                    <span class="rating-distribution-label">
                        ${5 - index} ★
                    </span>

                    <div class="rating-distribution-track"
                         role="progressbar"
                         aria-label="${5 - index} star ratings"
                         aria-valuenow="${percent(number)}"
                         aria-valuemin="0"
                         aria-valuemax="100">

                        <span style="width:${percent(number)}%">
                        </span>
                    </div>

                    <span class="rating-distribution-count">
                        ${number}
                    </span>

                </div>

            `).join("")}

        </div>

        <!-- TRAVELLER REVIEWS -->
        <div class="compact-review-heading">
            Traveller reviews
        </div>

        <div class="compact-review-list">
            ${compactReviews || `
                <p class="review-no-comment">
                    No traveller reviews yet.
                </p>
            `}
        </div>

        <!-- EXPAND / COLLAPSE REVIEWS -->
        ${reviews.length > 1 ? `

            <button
                type="button"
                class="compact-toggle-reviews"
                data-toggle-destination="${escapeHTML(
                    destination.destination_id
                )}"
                aria-expanded="${expanded}">

                ${expanded
                    ? "Show fewer reviews"
                    : `View all ${reviews.length} reviews`
                }

            </button>

        ` : ""}
    `;

    return card;
}


// Search, filter and sort destination ratings
function filterRatingsAndReviews() {
    const container = document.getElementById(
        "ratings-reviews-list"
    );

    if (!container) return;

    const searchText = (
        document.getElementById("reviews-search")?.value || ""
    ).trim().toLowerCase();

    const interest = document.getElementById(
        "reviews-interest-filter"
    )?.value || "all";

    const sort = document.getElementById(
        "reviews-sort-filter"
    )?.value || "highest";

    const minimum = Number(
        document.getElementById(
            "reviews-minimum-rating"
        )?.value || 0
    );

    const matched = allRatingsReviewsData.filter(
        destination => {
            const search = `
                ${destination.destination_name || ""}
                ${destination.state || ""}
            `.toLowerCase();

            return (
                search.includes(searchText) &&
                (
                    interest === "all" ||
                    reviewInterestTags(destination).includes(interest)
                ) &&
                Number(destination.average_rating) >= minimum
            );
        }
    );

    matched.sort((a, b) => {
        if (sort === "most") {
            return (
                Number(b.total_ratings) -
                Number(a.total_ratings)
            ) || (
                Number(b.average_rating) -
                Number(a.average_rating)
            );
        }

        if (sort === "lowest") {
            return (
                Number(a.average_rating) -
                Number(b.average_rating)
            ) || (
                Number(b.total_ratings) -
                Number(a.total_ratings)
            );
        }

        if (sort === "name") {
            return String(a.destination_name).localeCompare(
                String(b.destination_name)
            );
        }

        return (
            Number(b.average_rating) -
            Number(a.average_rating)
        ) || (
            Number(b.total_ratings) -
            Number(a.total_ratings)
        );
    });

    container.replaceChildren();

    if (matched.length) {
        const fragment = document.createDocumentFragment();

        matched.forEach(destination => {
            fragment.appendChild(
                renderReviewDashboardCard(destination)
            );
        });

        container.appendChild(fragment);

    } else {
        const empty = document.createElement("div");

        empty.className =
            "empty-state reviews-dashboard-empty";

        empty.textContent = allRatingsReviewsData.length
            ? "No destinations match these filters. Try another interest or rating."
            : "No destination ratings have been submitted yet.";

        container.appendChild(empty);
    }

    const count = document.getElementById(
        "reviews-search-count"
    );

    if (count) {
        count.textContent =
            `Showing ${matched.length} of ` +
            `${allRatingsReviewsData.length} rated destinations`;
    }
}


// Refresh ratings after submitting a new review
async function refreshRatingInformation() {
    await loadDestinationRatings();
    await loadAllRatingsAndReviews();
}


// Set up search and filters
[
    "reviews-search",
    "reviews-interest-filter",
    "reviews-sort-filter",
    "reviews-minimum-rating"

].forEach(id => {
    const element = document.getElementById(id);

    element?.addEventListener(
        id === "reviews-search" ? "input" : "change",
        filterRatingsAndReviews
    );
});


// Clear search
document.getElementById("clear-reviews-search")
    ?.addEventListener("click", () => {

        const input = document.getElementById(
            "reviews-search"
        );

        if (input) {
            input.value = "";
            filterRatingsAndReviews();
            input.focus();
        }
    });


// Reset all filters
document.getElementById("reviews-clear-filters")
    ?.addEventListener("click", () => {

        const defaults = {
            "reviews-interest-filter": "all",
            "reviews-sort-filter": "highest",
            "reviews-minimum-rating": "0"
        };

        Object.entries(defaults).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.value = value;
        });

        const search = document.getElementById(
            "reviews-search"
        );

        if (search) search.value = "";

        filterRatingsAndReviews();
    });


// View all / show fewer reviews
document.getElementById("ratings-reviews-list")
    ?.addEventListener("click", event => {

        const button = event.target.closest(
            "[data-toggle-destination]"
        );

        if (!button) return;

        const id = button.dataset.toggleDestination;

        if (expandedReviewDestinationIds.has(id)) {
            expandedReviewDestinationIds.delete(id);
        } else {
            expandedReviewDestinationIds.add(id);
        }

        filterRatingsAndReviews();
    });






// Close the review panel with Escape or by clicking the backdrop.
document.addEventListener("keydown", event => {
 if(event.key==="Escape") {document.getElementById("review-modal")?.classList.add("hidden"); selectedReviewDestination=null;}
});
document.getElementById("review-modal")?.addEventListener("click", event => {
 if(event.target.id==="review-modal") {event.currentTarget.classList.add("hidden"); selectedReviewDestination=null;}
});


async function updateDestinationRatingDisplaysForCard(card) {
    const ratingDisplay = card.querySelector(
        ".destination-rating-inline"
    );

    if (!ratingDisplay) return;

    const destinationId = ratingDisplay.dataset.ratingId;

    function showRating(average, count) {
        if (count <= 0 || !Number.isFinite(average)) {
            ratingDisplay.innerHTML = `
                <span class="rating-star">☆</span>
                <span class="rating-empty">No ratings yet</span>
            `;
            return;
        }

        ratingDisplay.innerHTML = `
            <span class="rating-star">★</span>
            <span class="rating-value">${average.toFixed(1)}</span>
            <span class="rating-count">
                (${count} ${count === 1 ? "review" : "reviews"})
            </span>
        `;
    }

    const cachedRating = destinationRatings[destinationId];

    if (cachedRating && Number(cachedRating.total_ratings) > 0) {
        showRating(
            Number(cachedRating.average_rating),
            Number(cachedRating.total_ratings)
        );
        return;
    }

    ratingDisplay.textContent = "Loading rating...";

    try {
        const data = await apiRequest(
            `/api/travel/destinations/${encodeURIComponent(destinationId)}/reviews`
        );

        if (!ratingDisplay.isConnected) return;

        const average = Number(data.average_rating);
        const count = Number(data.total_reviews || 0);

        destinationRatings[destinationId] = {
            average_rating: average,
            total_ratings: count
        };

        showRating(average, count);

    } catch (error) {
        console.error("Rating loading error:", error);
        ratingDisplay.textContent = "Rating unavailable";
    }
}


/* ==========================================
   AUTOMATIC CHRISTMAS COLOUR THEME
   ========================================== */

function updateFestivalColourTheme() {

    const isChristmas =
        festivalMode &&
        selectedFestivalId === "christmas";

    document.body.classList.toggle(
        "christmas-theme",
        isChristmas
    );

}
