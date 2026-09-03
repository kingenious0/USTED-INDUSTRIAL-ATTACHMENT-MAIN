import io
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.extensions import db
from app.models.attachment import AttachmentRecord
from app.models.activity import WeeklyActivity


class WatermarkCanvas(canvas.Canvas):
    """
    Custom canvas that prints a diagonal 'UNVERIFIED DRAFT' watermark
    if the activity sheet has not been locked by the student.
    """
    def __init__(self, *args, is_unlocked: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_unlocked = is_unlocked

    def showPage(self):
        if self.is_unlocked:
            self.saveState()
            self.setFont("Helvetica-Bold", 52)
            # Subtle translucent red watermark
            self.setFillColor(colors.HexColor('#DC2626'), alpha=0.14)
            # Center of Landscape A4 (841.89 x 595.27)
            self.translate(420, 297)
            self.rotate(28)
            self.drawCentredString(0, 0, "UNVERIFIED DRAFT")
            self.restoreState()
        super().showPage()


def _get_landscape_styles():
    """Builds typography styles tailored for Landscape A4 sheets."""
    base_styles = getSampleStyleSheet()
    styles = {}

    styles['UnivHeader'] = ParagraphStyle(
        'UnivHeader',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.HexColor('#6B022D'),
        alignment=1,  # Centered
        spaceAfter=1
    )

    styles['SubHeader'] = ParagraphStyle(
        'SubHeader',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#0F172A'),
        alignment=1,
        spaceAfter=3
    )

    styles['SheetTitle'] = ParagraphStyle(
        'SheetTitle',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=13,
        textColor=colors.HexColor('#8C033B'),
        alignment=1,
        spaceAfter=4
    )

    styles['MetaText'] = ParagraphStyle(
        'MetaText',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#334155')
    )

    styles['MetaTextBold'] = ParagraphStyle(
        'MetaTextBold',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0F172A')
    )

    styles['TableHeader'] = ParagraphStyle(
        'TableHeader',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )

    styles['TableCell'] = ParagraphStyle(
        'TableCell',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0F172A')
    )

    styles['TableCellCenter'] = ParagraphStyle(
        'TableCellCenter',
        parent=styles['TableCell'],
        alignment=1
    )

    styles['TableCellBold'] = ParagraphStyle(
        'TableCellBold',
        parent=styles['TableCell'],
        fontName='Helvetica-Bold'
    )

    styles['SectionTitle'] = ParagraphStyle(
        'SectionTitle',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#6B022D'),
        spaceAfter=2
    )

    styles['SectionNote'] = ParagraphStyle(
        'SectionNote',
        parent=base_styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=3
    )

    styles['StampLabel'] = ParagraphStyle(
        'StampLabel',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        alignment=1,
        textColor=colors.HexColor('#6B022D')
    )

    styles['StampSub'] = ParagraphStyle(
        'StampSub',
        parent=base_styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=6.5,
        leading=8.5,
        alignment=1,
        textColor=colors.HexColor('#64748B')
    )

    return styles


def generate_weekly_sheet_pdf(attachment_id: int, week_number: int) -> bytes:
    """
    Generates the official Weekly Activity Sheet PDF in Landscape A4.

    Features:
      - Orientation: Landscape A4 (841.89 x 595.27 points).
      - Table: Mon–Fri logs with time, activities, skills, and student remarks.
      - Physical Verification Container: Ruled lines for handwritten supervisor
        comments, supervisor signature, date, and a bordered rectangular box
        of at least 60mm x 35mm labeled: 'AFFIX OFFICIAL COMPANY WET-INK STAMP'.
      - Watermarking: If week is unlocked, stamps 'UNVERIFIED DRAFT' diagonally
        across the sheet.
    """
    attachment = db.session.get(AttachmentRecord, attachment_id)
    if not attachment:
        raise ValueError(f"AttachmentRecord #{attachment_id} not found.")

    weekly_activity = WeeklyActivity.query.filter_by(
        attachment_id=attachment.id,
        week_number=week_number
    ).first()

    if not weekly_activity:
        raise ValueError(f"WeeklyActivity Week {week_number} for Attachment #{attachment_id} not found.")

    student = attachment.student
    is_unlocked = not weekly_activity.is_locked

    buffer = io.BytesIO()

    # Landscape A4 with compact margins to guarantee single-page fitting
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=20,
        bottomMargin=20
    )

    styles = _get_landscape_styles()
    story = []

    # 1. Institutional Header
    story.append(Paragraph(
        "UNIVERSITY OF SKILLS TRAINING AND ENTREPRENEURIAL DEVELOPMENT (USTED)",
        styles['UnivHeader']
    ))
    story.append(Paragraph(
        "INDUSTRIAL LIAISON OFFICE &bull; WORKPLACE EXPERIENCE LEARNING (WEL)",
        styles['SubHeader']
    ))

    # Lock Status Text in title
    lock_badge = "[OFFICIALLY LOCKED]" if weekly_activity.is_locked else "[DRAFT / UNLOCKED]"
    story.append(Paragraph(
        f"<b>WEEKLY ACTIVITY LOG SHEET — WEEK {weekly_activity.week_number}</b> &nbsp;&nbsp; {lock_badge}",
        styles['SheetTitle']
    ))

    # 2. Student & Organization Particulars Bar
    start_str = weekly_activity.start_date.strftime('%d/%m/%Y')
    end_str = weekly_activity.end_date.strftime('%d/%m/%Y')
    org_display = attachment.target_organization or "To be confirmed by Host Acceptance"

    particulars_data = [
        [
            Paragraph("<b>Student Name:</b>", styles['MetaTextBold']),
            Paragraph(student.full_name, styles['MetaText']),
            Paragraph("<b>Index Number:</b>", styles['MetaTextBold']),
            Paragraph(student.index_number, styles['MetaText']),
            Paragraph("<b>Academic Year:</b>", styles['MetaTextBold']),
            Paragraph(attachment.academic_year, styles['MetaText'])
        ],
        [
            Paragraph("<b>Programme:</b>", styles['MetaTextBold']),
            Paragraph(f"{student.programme} (Level {student.current_level})", styles['MetaText']),
            Paragraph("<b>Host Org:</b>", styles['MetaTextBold']),
            Paragraph(org_display, styles['MetaText']),
            Paragraph("<b>Period:</b>", styles['MetaTextBold']),
            Paragraph(f"{start_str} to {end_str}", styles['MetaText'])
        ]
    ]

    t_meta = Table(particulars_data, colWidths=[70, 240, 75, 140, 75, 190])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FDF2F5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    # 3. Monday–Friday Activities Table
    table_headers = [
        Paragraph("<b>Day / Date</b>", styles['TableHeader']),
        Paragraph("<b>Hours / Time</b>", styles['TableHeader']),
        Paragraph("<b>Key Tasks & Learning Outcomes Conducted</b>", styles['TableHeader']),
        Paragraph("<b>Skills Demonstrated / Remarks</b>", styles['TableHeader'])
    ]
    activities_rows = [table_headers]

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in days:
        entry = weekly_activity.get_entry_for_day(day)
        date_str = entry.date.strftime('%d/%m/%Y') if entry else ""
        day_label = f"<b>{day}</b><br/>{date_str}"
        hours_str = f"{entry.start_time or '08:00'} - {entry.end_time or '17:00'}" if entry and (entry.start_time or entry.end_time) else "—"
        tasks_str = entry.key_tasks if (entry and entry.key_tasks) else "<i>No specific task recorded for this day</i>"
        skills_str = entry.skills_demonstrated if (entry and entry.skills_demonstrated) else ""
        if entry and entry.remarks:
            skills_str += f"<br/><b>Remarks:</b> {entry.remarks}" if skills_str else f"<b>Remarks:</b> {entry.remarks}"
        if not skills_str:
            skills_str = "—"

        activities_rows.append([
            Paragraph(day_label, styles['TableCellCenter']),
            Paragraph(hours_str, styles['TableCellCenter']),
            Paragraph(tasks_str, styles['TableCell']),
            Paragraph(skills_str, styles['TableCell'])
        ])

    # Usable width: 841.89 - 48 = 793.89
    t_activities = Table(activities_rows, colWidths=[80, 80, 390, 240])
    t_activities.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6B022D')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FDF2F5')])
    ]))
    story.append(t_activities)
    story.append(Spacer(1, 6))

    # 4. Physical Workplace Supervisor Verification Container
    # Contains: Ruled lines for comments, supervisor signature, date,
    # and a bordered rectangular stamp box of at least 60mm x 35mm
    # labeled "AFFIX OFFICIAL COMPANY WET-INK STAMP".
    # 60mm = ~170pt, 35mm = ~99pt
    stamp_box_content = [
        Paragraph("<b>AFFIX OFFICIAL COMPANY WET-INK STAMP</b>", styles['StampLabel']),
        Spacer(1, 2),
        Paragraph("<i>(Wet-ink company stamp required)</i>", styles['StampSub']),
        Spacer(1, 40), # Generous wet-ink stamping area
        Paragraph("Verified & Stamped by Enterprise", styles['StampSub'])
    ]

    comment_lines = (
        "<b>Supervisor Comments on Student Performance & Diligence:</b><br/>"
        "____________________________________________________________________________________________________________________________________<br/><br/>"
        "____________________________________________________________________________________________________________________________________<br/><br/>"
        "<b>Supervisor Name:</b> _________________________________________________ &nbsp;&nbsp;&nbsp;&nbsp; "
        "<b>Contact Phone:</b> ____________________________________<br/><br/>"
        "<b>Signature:</b> _______________________________________________________ &nbsp;&nbsp;&nbsp;&nbsp; "
        "<b>Date:</b> _______ / _______ / 2026"
    )

    verif_row = [
        [
            Paragraph(comment_lines, styles['TableCell']),
            stamp_box_content
        ]
    ]

    # Total width: 595 + 195 = 790pt. Stamp column: 195pt x ~105pt (approx 68mm x 37mm, exceeds 60mm x 35mm)
    t_verif = Table(verif_row, colWidths=[595, 195])
    t_verif.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 0.75, colors.HexColor('#6B022D')),
        ('BOX', (1, 0), (1, 0), 1.5, colors.HexColor('#8C033B')), # Bordered rectangular stamp box
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#FAFAFA')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))

    story.append(Paragraph("<b>PHYSICAL WORKPLACE SUPERVISOR VERIFICATION & WET-INK STAMP</b>", styles['SectionTitle']))
    story.append(Paragraph(
        "<i>(To be completed in physical handwriting, signed, and endorsed with official wet-ink company stamp by workplace supervisor)</i>",
        styles['SectionNote']
    ))
    story.append(KeepTogether([t_verif]))

    # Custom canvas maker to watermark "UNVERIFIED DRAFT" if unlocked
    def make_canvas(*args, **kwargs):
        return WatermarkCanvas(*args, is_unlocked=is_unlocked, **kwargs)

    doc.build(story, canvasmaker=make_canvas)
    buffer.seek(0)
    return buffer.getvalue()
