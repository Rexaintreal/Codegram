const postContainer = document.getElementById('post-container');
const loadingMessage = document.querySelector('.loading-message');

let isLoading = false;
let page = 1;

window.addEventListener('scroll', () => {
  const { scrollTop, clientHeight, scrollHeight } = document.documentElement;

  if (scrollTop + clientHeight >= scrollHeight - 5 && !isLoading) {
    loadMorePosts();
  }
});

function loadMorePosts() {
  isLoading = true;
  loadingMessage.style.display = 'block';

  // Simulate loading more posts
  setTimeout(() => {
    fetch(`/get_more_posts?page=${page}`)
      .then(response => response.json())
      .then(data => {
        const posts = data.posts;
        if (posts.length > 0) {
          const postWrapper = document.querySelector('.post-wrapper');
          for (let post of posts) {
            const newPost = createPostElement(post);
            postWrapper.insertBefore(newPost, postWrapper.firstChild);
          }
          page++;
        } else {
          loadingMessage.textContent = 'No more posts.';
        }
      })
      .catch(error => {
        console.error('Error:', error);
        loadingMessage.textContent = 'Failed to load posts.';
      })
      .finally(() => {
        isLoading = false;
        loadingMessage.style.display = 'none';
      });
  }, 1000);
}

function createPostElement(post) {
  const postElement = document.createElement('div');
  postElement.classList.add('post');
  postElement.dataset.id = post.id;

  const postInfo = document.createElement('div');
  postInfo.classList.add('post-info');

  const usernameLink = document.createElement('a');
  usernameLink.href = `/profile/${post.username}`;
  usernameLink.classList.add('username');
  usernameLink.textContent = post.username;
  postInfo.appendChild(usernameLink);

  postElement.appendChild(postInfo);

  const postContent = document.createElement('div');
  postContent.classList.add('post-content');
  postContent.innerHTML = `<pre><code>${post.content}</code></pre>`;
  postElement.appendChild(postContent);

  const postFeatures = document.createElement('div');
  postFeatures.classList.add('post-features');

  const buttons = document.createElement('div');
  buttons.classList.add('buttons');

  const likeForm = document.createElement('form');
  likeForm.action = '/like_post';
  likeForm.method = 'POST';

  const likeInput = document.createElement('input');
  likeInput.type = 'hidden';
  likeInput.name = 'post_id';
  likeInput.value = post.id;
  likeForm.appendChild(likeInput);

  const likeButton = document.createElement('button');
  likeButton.type = 'submit';
  likeButton.classList.add('like-icon');
  likeButton.name = 'like_button';

  const likeIcon = document.createElement('img');
  likeIcon.src = '/static/images/like.png';
  likeIcon.alt = 'Like';
  likeButton.appendChild(likeIcon);

  likeForm.appendChild(likeButton);
  buttons.appendChild(likeForm);

  const dislikeForm = document.createElement('form');
  dislikeForm.action = '/dislike_post';
  dislikeForm.method = 'POST';

  const dislikeInput = document.createElement('input');
  dislikeInput.type = 'hidden';
  dislikeInput.name = 'post_id';
  dislikeInput.value = post.id;
  dislikeForm.appendChild(dislikeInput);

  const dislikeButton = document.createElement('button');
  dislikeButton.type = 'submit';
  dislikeButton.classList.add('dislike-icon');
  dislikeButton.name = 'dislike_button';

  const dislikeIcon = document.createElement('img');
  dislikeIcon.src = '/static/images/dislike.png';
  dislikeIcon.alt = 'Dislike';
  dislikeButton.appendChild(dislikeIcon);

  dislikeForm.appendChild(dislikeButton);
  buttons.appendChild(dislikeForm);

  const commentLink = document.createElement('a');
  commentLink.href = `/comment_post/${post.id}`;
  commentLink.classList.add('comment-icon');

  const commentIcon = document.createElement('img');
  commentIcon.src = '/static/images/comment.png';
  commentIcon.alt = 'Comment';
  commentLink.appendChild(commentIcon);

  buttons.appendChild(commentLink);

  postFeatures.appendChild(buttons);

  const likeCount = document.createElement('span');
  likeCount.classList.add('like-count');
  likeCount.textContent = post.like_count;
  postFeatures.appendChild(likeCount);

  postElement.appendChild(postFeatures);

  return postElement;
}