from django.db import IntegrityError, transaction

from authentication.models import Chapter, Subject, Syllabus, Topic


def create_syllabus(*, subject, title, academic_year="", description="", status="DRAFT", is_active=True):
    return Syllabus.objects.create(
        subject=subject,
        title=title,
        academic_year=academic_year,
        description=description,
        status=status,
        is_active=is_active,
    )


def create_chapter(*, syllabus, title, chapter_number, description="", status="DRAFT", is_active=True):
    return Chapter.objects.create(
        syllabus=syllabus,
        title=title,
        chapter_number=chapter_number,
        description=description,
        status=status,
        is_active=is_active,
    )


def create_topic(
    *,
    chapter,
    title,
    order,
    description="",
    video_url="",
    notes="",
    attachments=None,
    status="DRAFT",
    is_active=True,
):
    return Topic.objects.create(
        chapter=chapter,
        title=title,
        order=order,
        description=description,
        video_url=video_url,
        notes=notes,
        attachments=attachments or [],
        status=status,
        is_active=is_active,
    )


@transaction.atomic
def import_syllabus_structure(
    *,
    subject_id,
    title,
    academic_year="",
    description="",
    status="DRAFT",
    is_active=True,
    chapters_payload=None,
):
    subject = Subject.objects.filter(id=subject_id, is_active=True).first()
    if not subject:
        raise ValueError("subject_id is invalid or inactive")

    chapters_payload = chapters_payload or []
    if not chapters_payload:
        raise ValueError("No parsed chapters found")

    try:
        syllabus = create_syllabus(
            subject=subject,
            title=title,
            academic_year=academic_year,
            description=description,
            status=status,
            is_active=is_active,
        )
    except IntegrityError as exc:
        raise ValueError(f"Could not create syllabus: {exc}") from exc

    chapters_created = 0
    topics_created = 0

    seen_chapter_numbers = set()
    for chapter_data in chapters_payload:
        chapter_number = int(chapter_data.get("chapter_number", 0) or 0)
        chapter_title = (chapter_data.get("title") or "").strip()
        if chapter_number <= 0 or not chapter_title:
            continue
        if chapter_number in seen_chapter_numbers:
            continue
        seen_chapter_numbers.add(chapter_number)

        chapter = create_chapter(
            syllabus=syllabus,
            title=chapter_title,
            chapter_number=chapter_number,
            status=status,
            is_active=is_active,
        )
        chapters_created += 1

        seen_topics = set()
        order_counter = 0
        for topic_title in chapter_data.get("topics", []):
            clean_topic_title = (topic_title or "").strip()
            if not clean_topic_title:
                continue
            normalized = clean_topic_title.lower()
            if normalized in seen_topics:
                continue
            seen_topics.add(normalized)
            order_counter += 1
            create_topic(
                chapter=chapter,
                title=clean_topic_title,
                order=order_counter,
                status=status,
                is_active=is_active,
            )
            topics_created += 1

    if chapters_created == 0:
        raise ValueError("No valid chapters found to create")

    return {
        "syllabus": syllabus,
        "chapters_created": chapters_created,
        "topics_created": topics_created,
    }
