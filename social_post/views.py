import json
import os
import time

import openai
import requests
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

from social_post.models import Post, PostHistory, LinkedAccount

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY")

MASTODON_INSTANCE = os.getenv("SOCIAL_AUTH_MASTODON_INSTANCE")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def generate_post(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        title = data.get("title", "").strip()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return JsonResponse({"error": "Prompt is required"}, status=400)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a social media assistant. Generate a well-formatted social media post. Do NOT include titles."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7
        )

        if not response.choices or not response.choices[0].message.content:
            return JsonResponse({"error": "AI did not return a valid response"}, status=500)

        generated_text = response.choices[0].message.content.strip()
        formatted_text = "\n".join(line.strip() for line in generated_text.split("\n") if line.strip())

        if not formatted_text:
            return JsonResponse({"error": "Generated post is empty"}, status=500)

        post = Post.objects.create(title=title, prompt=prompt, content=formatted_text)

        return JsonResponse({"title": post.title, "post": formatted_text, "id": post.id}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

def list_posts(request):
    posts = Post.objects.all().order_by('-created_at')
    post_list = [{"id": post.id, "prompt": post.prompt, "title": post.title, "content": post.content, "created_at": post.created_at.strftime('%Y-%m-%d %H:%M:%S')} for post in posts]
    return JsonResponse({"posts": post_list}, status=200)

def post_history(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    history_entries = PostHistory.objects.filter(post=post).order_by("-edited_at")
    history_list = [{"edited_at": entry.edited_at.strftime("%Y-%m-%d %H:%M:%S"), "previous_content": entry.previous_content} for entry in history_entries]
    return JsonResponse({"history": history_list})

def view_posts(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'social_post/posts.html', {'posts': posts})

@csrf_exempt
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, deleted_at__isnull=True)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            new_title = data.get("title", "").strip()
            new_content = data.get("content", "").strip()

            if not new_title or not new_content:
                return JsonResponse({"success": False, "error": "Title and content cannot be empty"}, status=400)

            PostHistory.objects.create(post=post, previous_content=post.content)

            post.title = new_title
            post.content = new_content
            post.save()

            return JsonResponse({"success": True, "message": "Post updated!", "new_title": post.title, "new_content": post.content})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

def delete_post(request, post_id):
    if request.method == "DELETE":
        try:
            post = Post.objects.get(id=post_id)
            post.deleted_at = time.timezone.now()
            post.save()
            return JsonResponse({"success": True})
        except Post.DoesNotExist:
            return JsonResponse({"success": False, "error": "Post not found"})

def check_auth(request):
    return JsonResponse({"authenticated": request.user.is_authenticated})

# Mastodon posting functions
def send_mastodon_post(message, access_token):
    if not access_token or not MASTODON_INSTANCE:
        return {"success": False, "error": "Mastodon credentials not configured properly"}

    url = f"{MASTODON_INSTANCE}/api/v1/statuses"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(url, headers=headers, data={"status": message})

    if response.ok:
        return {"success": True, "message": "Posted successfully!"}
    else:
        return {"success": False, "error": response.text}


def get_linked_accounts(request):
    """Return all linked accounts, but handle unauthenticated users properly."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "User is not authenticated"}, status=403)

    try:
        accounts = LinkedAccount.objects.filter(user=request.user)
        data = [{"platform": acc.platform, "username": acc.username} for acc in accounts]
        return JsonResponse({"linked_accounts": data})
    except Exception as e:
        return JsonResponse({"error": f"Failed to fetch linked accounts: {str(e)}"}, status=500)



@csrf_exempt
def link_mastodon_account(request):
    """Link a Mastodon account without forcing Django login."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "User is not authenticated"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)  # ✅ Ensure JSON parsing works
        access_token = data.get("access_token")
        username = data.get("username")

        if not access_token or not username:
            return JsonResponse({"error": "Missing Mastodon token or username"}, status=400)

        # ✅ Save token in LinkedAccount Model
        LinkedAccount.objects.update_or_create(
            user=request.user,
            platform="mastodon",
            defaults={"access_token": access_token, "username": username}
        )

        return JsonResponse({"success": "Mastodon account linked!"})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

def unlink_account(request):
    """Unlink a social media account."""
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({"error": "User is not authenticated"}, status=403)

        try:
            data = json.loads(request.body)
            platform = data.get("platform")

            if not platform:
                return JsonResponse({"error": "Platform is required"}, status=400)

            # Remove account from the database
            LinkedAccount.objects.filter(user=request.user, platform=platform).delete()

            return JsonResponse({"success": f"{platform} account unlinked successfully!"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)