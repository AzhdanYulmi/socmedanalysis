// Get CSRF Token from Hidden Input (More Reliable)
function getCSRFToken() {
    let csrfToken = document.cookie
        .split("; ")
        .find(row => row.startsWith("csrftoken="))
        ?.split("=")[1];

    if (!csrfToken) {
        console.error("❌ CSRF token not found in cookies!");
        alert("⚠️ CSRF token missing! Try refreshing the page.");
    } else {
        console.log(`🔑 CSRF Token Retrieved: ${csrfToken}`);
    }

    return csrfToken;
}

// Fetch Linked Accounts and Update UI
function fetchLinkedAccounts() {
    fetch("/linked-accounts/")
    .then(response => response.json())
    .then(data => {
        console.log("🔗 Linked accounts:", data);

        let linkedAccountsSection = document.getElementById("linkedAccountsList");
        linkedAccountsSection.innerHTML = ""; // Clear previous content

        if (data.linked_accounts.length === 0) {
            linkedAccountsSection.innerHTML = `<li class="list-group-item text-muted">No accounts linked.</li>`;
        } else {
            data.linked_accounts.forEach(account => {
                linkedAccountsSection.innerHTML += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        ${account.platform.toUpperCase()} - ${account.username}
                        <button class="btn btn-sm btn-danger unlink-btn" data-platform="${account.platform}">
                            Unlink
                        </button>
                    </li>
                `;
            });
        }

        // Disable or enable Mastodon post button
        let isMastodonLinked = data.linked_accounts.some(account => account.platform === "mastodon");
        let mastodonButtons = document.querySelectorAll(".mastodon-button");

        mastodonButtons.forEach(button => {
            if (!isMastodonLinked) {
                button.disabled = true;
                button.classList.add("disabled");
                button.setAttribute("title", "You must link a Mastodon account first!");
            } else {
                button.disabled = false;
                button.classList.remove("disabled");
                button.removeAttribute("title");
            }
        });

    })
    .catch(error => console.error("❌ Error fetching linked accounts:", error));
}

// Ensure linked accounts update on page load
document.addEventListener("DOMContentLoaded", fetchLinkedAccounts);

// Unlink Account
document.body.addEventListener("click", function (event) {
    if (event.target.classList.contains("unlink-btn")) {
        const platform = event.target.getAttribute("data-platform");

        if (!confirm(`⚠️ Are you sure you want to unlink ${platform}?`)) return;

        fetch(`/unlink-account/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken()
            },
            body: JSON.stringify({ platform: platform })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`✅ Successfully unlinked ${platform}!`);
                fetchLinkedAccounts(); // Refresh UI after unlinking
            } else {
                alert(`❌ Failed to unlink ${platform}: ${data.error}`);
            }
        })
        .catch(error => console.error("❌ Error unlinking account:", error));
    }
});

// Generate Post
document.getElementById("postForm").addEventListener("submit", function(event) {
    console.log("📨 Submitting form...");
    event.preventDefault();

    const title = document.getElementById("titleInput").value.trim();
    const prompt = document.getElementById("promptInput").value.trim();

    if (!title || !prompt) {
        alert("⚠️ Please enter both a title and a prompt!");
        return;
    }

    document.getElementById("loading").style.display = "block";

    axios.post("/generate/", { prompt: prompt }, {
            headers: { "X-CSRFToken": getCSRFToken() }
        })
        .then(response => {
            console.log("✅ Post generated successfully!", response.data);

            // 🚀 Directly use the response data
            const post = response.data;
            if (!post.post || post.post.trim() === "undefined") {
                console.error("❌ Invalid post content received:", post.post);
                alert("❌ Error: Generated post content is invalid.");
                return;
            }

            // ✅ Render the post IMMEDIATELY
            renderPost(title, prompt, post.post, post.id);

            // Clear input fields
            document.getElementById("titleInput").value = "";
            document.getElementById("promptInput").value = "";
        })
        .catch(error => {
            console.error("❌ Error generating post:", error);
            document.getElementById("error-message").innerText = error.response?.data?.error || "Unknown error";
            document.getElementById("error-message").style.display = "block";
        })
        .finally(() => {
            document.getElementById("loading").style.display = "none";
        });
});

/**
 * ✅ Waits for the post to be ready before rendering it
 */
function waitForPostToBeReady(postId, title, prompt, attempts = 5) {
    if (attempts <= 0) {
        console.error("❌ Post still not found after retries. Giving up.");
        alert("❌ Error: Post generation failed. Please try again.");
        return;
    }

    console.log(`⏳ Checking if post ${postId} is ready... (${attempts} attempts left)`);

    axios.get(`/get-post/${postId}/`)
    .then(response => {
        if (response.data.content && response.data.content.trim() !== "undefined") {
            console.log("✅ Post is ready! Rendering...");
            renderPost(title, prompt, response.data.content, postId);
        } else {
            console.warn("⚠️ Post not fully ready yet. Retrying in 500ms...");
            setTimeout(() => waitForPostToBeReady(postId, title, prompt, attempts - 1), 5000);
        }
    })
    .catch(error => {
        console.warn("⚠️ Error fetching post, retrying...");
        setTimeout(() => waitForPostToBeReady(postId, title, prompt, attempts - 1), 5000);
    });
}

function renderPost(title, prompt, content, postId) {
    console.log("🎨 Rendering post:", { title, content, postId });

    const postContainer = document.getElementById("postsContainer");

    const newPost = `
        <div class="card mt-3 p-3">
            <h5 class="card-title">${title}</h5>
            <p class="card-text">${content}</p>
            <small class="text-muted">Generated just now</small>

            <div class="hidden-prompt" style="display: none;">${prompt}</div>

            <div class="d-flex flex-wrap gap-2 mt-3">
                <button class="btn btn-secondary show-prompt-btn">Show Prompt</button>
                <button class="btn btn-info view-history-btn" data-post-id="${postId}">View Edit History</button>
                <button class="btn btn-warning edit-post-btn" data-post-id="${postId}">Edit</button>
                <button class="btn btn-danger delete-post-btn" data-post-id="${postId}">Delete</button>
                <button class="btn btn-primary mastodon-button" data-message="${content}">Post to Mastodon</button>
            </div>
        </div>
    `;

    postContainer.insertAdjacentHTML("afterbegin", newPost);
}



// Handle Mastodon Posting
document.body.addEventListener("click", function (event) {
    if (event.target.classList.contains("mastodon-button")) {
        let message = event.target.getAttribute("data-message").trim();

        if (!message || message.length === 0) {
            alert("⚠️ Cannot post an empty message!");
            return;
        }

        console.log(`📤 Sending post to Mastodon: "${message}"`);

        fetch("/mastodon-post/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken()
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            console.log("📩 Mastodon Response:", data);
            if (data.success) {
                alert("✅ Successfully posted to Mastodon!");
            } else {
                alert(`❌ Failed to post: ${data.error}`);
            }
        })
        .catch(error => console.error("❌ Error posting to Mastodon:", error));
    }
});

// Handle Mastodon Account Linking
document.addEventListener("DOMContentLoaded", function () {
    console.log("✅ script.js loaded!");

    document.getElementById("linkMastodonBtn").addEventListener("click", function () {
        const accessToken = prompt("Enter your Mastodon Access Token:");
        const username = prompt("Enter your Mastodon Username:");

        if (!accessToken || !username) {
            alert("⚠️ Linking failed: Missing access token or username.");
            return;
        }

        fetch("/link-mastodon/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken()
            },
            body: JSON.stringify({ access_token: accessToken, username: username })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error); });
            }
            return response.json();
        })
        .then(data => {
            alert("✅ Mastodon account linked successfully!");
            fetchLinkedAccounts(); // Refresh the linked accounts UI
        })
        .catch(error => console.error("❌ Error linking Mastodon:", error));
    });
});
