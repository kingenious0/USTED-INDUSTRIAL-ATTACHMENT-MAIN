from app.extensions import db
from app.models.user import User, UserRole
from app.models.student_master import StudentMaster


SAMPLE_STUDENTS = [
    {
        'index_number': 'USTED/2024/001',
        'full_name': 'Kofi Mensah Boateng',
        'programme': 'BSc. Information Technology Education',
        'department': 'Information Technology Education',
        'current_level': 300,
        'phone': '0244123456',
        'email': 'kofi.boateng@st.usted.edu.gh'
    },
    {
        'index_number': 'USTED/2024/002',
        'full_name': 'Abena Serwaa Osei',
        'programme': 'BSc. Electrical & Electronic Engineering Education',
        'department': 'Electrical Engineering',
        'current_level': 200,
        'phone': '0208987654',
        'email': 'abena.osei@st.usted.edu.gh'
    },
    {
        'index_number': 'USTED/2024/003',
        'full_name': 'Kwame Antwi-Boasiako',
        'programme': 'BSc. Mechanical Technology Education',
        'department': 'Mechanical Technology',
        'current_level': 400,
        'phone': '0277345678',
        'email': 'kwame.antwi@st.usted.edu.gh'
    },
    {
        'index_number': 'USTED/2024/004',
        'full_name': 'Esi Mansa Danquah',
        'programme': 'BSc. Construction Technology Management',
        'department': 'Construction & Wood Technology',
        'current_level': 100,
        'phone': '0555890123',
        'email': 'esi.danquah@st.usted.edu.gh'
    },
    {
        'index_number': 'USTED/2024/005',
        'full_name': 'Emmanuel Yaw Frimpong',
        'programme': 'BSc. Computer Science Education',
        'department': 'Information Technology Education',
        'current_level': 300,
        'phone': '0243567890',
        'email': 'emmanuel.frimpong@st.usted.edu.gh'
    },
    {
        'index_number': '5230100452',
        'full_name': 'Elliot Paakow Entsiwah',
        'programme': 'B.Sc. Information Technology Education',
        'department': 'Information Technology Education',
        'current_level': 300,
        'phone': '0240001122',
        'email': 'elliot.entsiwah@st.usted.edu.gh'
    }
]


def seed_database():
    """Seeds the database with initial users and student master data."""
    # 1. Seed Student Master Data
    created_students = {}
    for st_data in SAMPLE_STUDENTS:
        existing = StudentMaster.query.filter_by(index_number=st_data['index_number']).first()
        if not existing:
            student = StudentMaster(**st_data)
            db.session.add(student)
            db.session.flush()
            created_students[st_data['index_number']] = student
        else:
            created_students[st_data['index_number']] = existing

    # 2. Seed Users
    users_to_seed = [
        {
            'username': 'admin1',
            'email': 'admin@usted.edu.gh',
            'full_name': 'Dr. Kwame Asante (Liaison Head)',
            'role': UserRole.LIAISON_HEAD,
            'password': 'password123',
            'staff_id': 'USTED-ADM-001',
            'department': 'Industrial Liaison Directorate',
            'office_location': 'Central Administration, Block A, Room 102',
            'phone': '0241112233'
        },
        {
            'username': 'liaison1',
            'email': 'liaison1@usted.edu.gh',
            'full_name': 'Mrs. Faustina Arthur',
            'role': UserRole.LIAISON_OFFICER,
            'password': 'password123',
            'staff_id': 'USTED-LIA-0012',
            'department': 'Industrial Liaison Directorate',
            'office_location': 'Faculty of Technical Education, Block B, Room 204',
            'phone': '0242223344'
        },
        {
            'username': 'supervisor1',
            'email': 'supervisor1@usted.edu.gh',
            'full_name': 'Ing. Dr. Peter Owusu',
            'role': UserRole.ACADEMIC_SUPERVISOR,
            'password': 'password123',
            'staff_id': 'USTED-FAC-0142',
            'department': 'Information Technology Education',
            'office_location': 'Faculty of Applied Sciences, Block C, Room 305',
            'phone': '0243334455'
        },
        {
            'username': 'student1',
            'email': 'kofi.boateng@st.usted.edu.gh',
            'full_name': 'Kofi Mensah Boateng',
            'role': UserRole.STUDENT,
            'password': 'password123',
            'phone': '0244123456',
            'student_master': created_students.get('USTED/2024/001')
        },
        {
            'username': 'student2',
            'email': 'abena.osei@st.usted.edu.gh',
            'full_name': 'Abena Serwaa Osei',
            'role': UserRole.STUDENT,
            'password': 'password123',
            'phone': '0208987654',
            'student_master': created_students.get('USTED/2024/002')
        },
        {
            'username': '5230100452',
            'email': 'elliot.entsiwah@st.usted.edu.gh',
            'full_name': 'Elliot Paakow Entsiwah',
            'role': UserRole.STUDENT,
            'password': 'password123',
            'phone': '0240001122',
            'student_master': created_students.get('5230100452')
        }
    ]

    for u_data in users_to_seed:
        user = User.query.filter_by(username=u_data['username']).first()
        if not user:
            user = User(
                username=u_data['username'],
                email=u_data['email'],
                full_name=u_data['full_name'],
                role=u_data['role']
            )
            if 'student_master' in u_data and u_data['student_master']:
                user.student_master = u_data['student_master']
            user.set_password(u_data['password'])
            db.session.add(user)

        # Update particulars if not set
        if 'staff_id' in u_data and not user.staff_id:
            user.staff_id = u_data['staff_id']
        if 'department' in u_data and not user.department:
            user.department = u_data['department']
        if 'office_location' in u_data and not user.office_location:
            user.office_location = u_data['office_location']
        if 'phone' in u_data and not user.phone:
            user.phone = u_data['phone']

    db.session.commit()
    print("Database successfully initialized and seeded with demo accounts & student master data.")
