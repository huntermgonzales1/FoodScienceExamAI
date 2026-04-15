## Project summary (1–3 sentences)
Food Science Exam AI is a Streamlit web app that delivers case-study style food-science exams in a chat interface. Students authenticate via email one-time passcode (OTP), work through timed scenarios, and then finalize an attempt so an AI model can assign a numeric grade. Chats, attempts, and grades are stored in Supabase (Postgres) so instructors can review results and manage exam content.

## Diagrams

### Database schema / ER diagram
<img src="./ERD.png" width = "400">

## Demo video or GIF
[Watch the demo here](./Demo_video.mp4)
## What did you learn? (at least 3 key learnings)
### Learning 1
I feel that the biggest thing I learned doing this project was how to use streamlit and connect to a database. Doing this taught me a lot about security and how to properly set up a sign in page.

### Learning 2
Another large thing I learned was how to deal with Row Level Security (RLS) on supabase. I wanted professors to be able to access parts of the website that students could not. This meant I had to use fine grained RLS as well as JWTs to authorize and authenticate people before accessing certain pages

### Learning 3
The third thing I learned was how to properly use AI when coding. Before this project, I used AI more to ask simple questions, but becuase of the scope of the project, I had to rely more heavily on AI for certain parts. I learned how to prompt the AI to do very specific things, and do these changes incrementally to more easily find where the bugs are coming from. 

## Does your project integrate with AI? If yes, describe.
Yes. The app integrates with Google Gemini to power two parts of the exam experience:
- **Interactive exam chat**: student messages are sent to Gemini along with the scenario’s system instructions and the existing transcript, and the model returns the assistant response shown in the Streamlit chat UI.
- **Automated grading on finalization**: when a student clicks “Finalize and Grade,” the full transcript is sent to Gemini with a grading prompt; the model returns a numeric score (0–10) and justification, which are saved back to Supabase for later review.

## How did you use AI to build your project?
Since I have never used streamlit before, and never done RLS in supabase before, there was a lot I didn't know. Because of this, I used both codex and cursor while developing. I would almost always use the planning mode to make sure it would do what I asked it to and nothing more. I would always run manual tests after each iteration of what the agent did and verified other parts didn't break. I would also look over the code it wrote to try and understand what it did and why.

## Why this project is interesting to you
I found this project so interesting because I have never built an app or website before. It was a learning experience to know how to switch between pages, authenticate users, and even alter the UI a bit. It was also fun to integrate this with gemini in order for students to have a more interactive experience.

## Authentication
Authentication uses **Supabase Auth** with **email OTP (magic code)** sign-in. Students enter an email address, receive a one-time code, and verify it to establish a Supabase session; the app then uses the session access token for authenticated database calls. Authorization is enforced with a database-backed **allowlist** (`allowed_emails`) and (where applicable) **Row Level Security (RLS)** policies; the app also differentiates instructor capabilities using an `is_instructor` flag associated with the user profile/metadata so instructor-only pages and actions are gated.


## Scaling plan
As this is currently running on streamlit cloud community, it is quite limited in how it scales. The class that would be using this would only be about 15 students, so there will likely not be any problems with that. However, if this were to grow, we would need to host this on a AWS server. This is also only built for a single class currently and does not allow for different views or chat prompts for different classes. I would need to add more security in order to allow for different classes with different prompts, etc.

Since we are using Supabase for our database, they have a pretty generous free tier, which will likely not be reached. We may have to get to the point where we delete old chats, but I have not gotten to that. However, if we needed to scale, we could still just upgrade to their pro teir and keep our same setup.


