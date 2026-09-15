document.addEventListener("DOMContentLoaded", () => {
    const loadButton =
        document.getElementById("loadStudentsButton");

    const result =
        document.getElementById("jsonStudentResult");

    const enrollButton =
        document.getElementById("enrollStudentButton");

    const studentSelect =
        document.getElementById("studentSelect");

    const enrollmentResult =
        document.getElementById("enrollmentResult");

    /*
     * GET example:
     *
     * Classes page
     *      ↓
     * classes:students_json URL
     *      ↓
     * Classes view
     *      ↓
     * JsonResponse
     *      ↓
     * JavaScript
     */
    if (loadButton) {
        loadButton.addEventListener("click", async () => {
            const url = loadButton.dataset.url;

            result.textContent = "Loading...";

            try {
                const response = await fetch(url);

                if (!response.ok) {
                    throw new Error(
                        `HTTP ${response.status}`
                    );
                }

                const data = await response.json();

                if (data.students.length === 0) {
                    result.textContent =
                        "No students are enrolled.";
                    return;
                }

                result.textContent = data.students
                    .map(
                        student =>
                            `${student.student_id} - ${student.name}`
                    )
                    .join("\n");
            } catch (error) {
                console.error(error);
                result.textContent =
                    "Unable to load students.";
            }
        });
    }

    /*
     * POST example:
     *
     * JavaScript
     *      ↓
     * Classes enroll URL
     *      ↓
     * Django view
     *      ↓
     * Database
     *      ↓
     * JSON
     *      ↓
     * JavaScript
     */
    if (enrollButton) {
        enrollButton.addEventListener("click", async () => {
            const studentId = studentSelect.value;
            const url = enrollButton.dataset.url;

            if (!studentId) {
                enrollmentResult.textContent =
                    "Please select a student.";
                return;
            }

            enrollmentResult.textContent = "Saving...";

            try {
                const response = await fetch(url, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": window.CRMS.csrfToken,
                    },
                    body: JSON.stringify({
                        student_id: studentId,
                    }),
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(
                        data.message || "Request failed."
                    );
                }

                enrollmentResult.textContent =
                    data.message;

                // Reload so the server-rendered table
                // immediately reflects the new enrollment.
                if (data.success) {
                    window.location.reload();
                }
            } catch (error) {
                console.error(error);
                enrollmentResult.textContent =
                    error.message ||
                    "Unable to enroll student.";
            }
        });
    }
});
