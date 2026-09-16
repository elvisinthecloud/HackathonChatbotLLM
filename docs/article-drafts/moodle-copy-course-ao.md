# Copy a course in Moodle

## Article record

- Article ID: `MOODLE-COPY-001`
- Status: Content approved by the user; not ingested or deployed
- Service/area: Moodle
- Discovery portal: MCeLE; portal location does not change the Moodle delivery area
- Allowed role: Academics Officer
- Course scope: General Moodle procedure; no specific course or course-association access restriction
- Content type: Adapted user-supplied procedure, not synthetic
- Provenance: Transcript, tutorial URL, MClearn course URL, and AO training reminder supplied by the user in this task; timestamps removed and wording edited for readability
- Original video URL: https://portal.mcele.usmc.mil/content/mcele-portal/en/media/detail.html?Id=8527A2A4B6B0
- Required training URL: https://elearning.mcele.usmc.mil/moodle/course/index.php?categoryid=1264
- Link verification: URLs supplied by the user; the web tool could not open either page. Page contents and access requirements have not been independently verified.
- Redistribution status: To be confirmed before public packaging; no license inferred

## Knowledge content

You need the **Academics Officer (AO) Moodle role** to copy or create courses. To copy an existing course:

1. From the Moodle dashboard, select the **Home** tab.
2. Navigate to the category containing the course you want to copy.
3. Select **More** in the upper-right corner, then select **Manage courses**.
4. Select the course's **Copy course** icon, shown as **two overlapping squares**.
5. In the pop-up form, enter the appropriate name for the new course.
6. For the **short name**, use either the full course name or the course acronym and associated number, such as **EWS 1349**.
7. Once all the information is entered, select **Copy and return** or **Copy and view**.
8. Wait for **Current Operation** to display **Complete**. The course copy is then complete.

For a visual walkthrough, watch the [Moodle course-copy video tutorial](https://portal.mcele.usmc.mil/content/mcele-portal/en/media/detail.html?Id=8527A2A4B6B0).

**AO training reminder:** Complete the required [MClearn courses—1100, 2100, and 3100](https://elearning.mcele.usmc.mil/moodle/course/index.php?categoryid=1264). Failure to complete the required training may result in removal of your AO permissions.

## Editorial and retrieval notes

- AO course-copy answers should end with the tutorial link and then the MClearn training reminder/link. Keep these supporting passages associated with the procedure during chunking/retrieval so the requested ending is available to the answer generator. Include this behavior in later answer checks.
- The training reminder describes a possible loss of permissions, not a claim that the selected user is noncompliant or has already lost access. No training deadline or course completion status was supplied.
- This article provides copying steps only. The role prerequisite also mentions course creation, but no creation procedure was supplied.
- EWS 1349 is an example supplied in the transcript, not a seeded demo course or a newly verified course mapping.
- Do not invent additional form fields, copy durations, button differences, or copied-content/enrollment behavior.
- This procedure must be restricted to AO in backend retrieval before any content, title/preview, citation, routing candidate, or follow-up result reaches another role.
- Instructor/Adjunct Faculty permission guidance is a separate article, `MOODLE-COPY-002`; do not combine the articles into a shared procedural chunk.
- These access rules describe the selected demo scenario, not a complete production Moodle permission model.
