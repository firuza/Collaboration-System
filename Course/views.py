from django.shortcuts import render, redirect
from .models import Course, Topics, Links, TopicArticle
from Community.models import CommunityCourses, Community, CommunityMembership
from .forms import TopicForm
from workflow.models import States
from django.http import Http404, HttpResponse
from BasicArticle.models import Articles
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import Group as Roles

def create_course(request):
	title = request.POST['name']
	body = request.POST['desc']
	state = States.objects.get(name='draft')
	try:
		course_image = request.FILES['course_image']
	except:
		course_image = None
	course = Course.objects.create(title=title, body=body, created_by=request.user, state=state, image=course_image)
	return course

def create_topics(request, pk):
	course = Course.objects.get(pk=pk)
	name = request.POST['name']
	parentid = request.POST['parent']
	if parentid == '':
		parent = None
	else:
		parent = Topics.objects.get(pk=parentid)
	topic = Topics.objects.create(name = name, parent=parent, course = course )
	return topic

def course_view(request, pk):
	try:
		course = CommunityCourses.objects.get(course=pk)
		if course.course.state == States.objects.get(name='draft') and course.course.created_by != request.user:
			return redirect('home')
		topics = Topics.objects.filter(course=pk)
		topic = topics.first()
		links = Links.objects.filter(topics = topic)
		token =""
		if request.user.is_authenticated:
			token, created = Token.objects.get_or_create(user=request.user)
			token = token.key
#		count = course_watch(request, course.course) #Shall add this later
	except CommunityCourses.DoesNotExist:
		raise Http404
	return render(request, 'view_course.html', {'course':course, 'topics':topics, 'token':token})

def course_edit(request, pk):
	if request.user.is_authenticated:
		course = Course.objects.get(pk=pk)
		if course.state == States.objects.get(name='draft') and course.created_by != request.user:
			return redirect('home')
		if request.method == 'POST':
			status = request.POST['status']
			if status == 'addtopic':
				create_topics(request,pk)
			if status == 'update':
				update_topic_name(request)
			if status == 'movetopic':
				isMoved = move_topic(request)
				if isMoved == False:
					message = 'A topic cannot be made a child of itself or any of its descendants.'
					url = 'course_edit'
					argument = pk
					return render(request, 'error.html', {'message':message, 'url':url, 'argument':argument})
			if status == 'deletetopic':
				delete_topic(request)
			return redirect('course_edit',pk=pk)
		else:
			try:
				course = CommunityCourses.objects.get(course=pk)
				topics = Topics.objects.filter(course=pk)
				form = TopicForm(course.course)
			except CommunityCourses.DoesNotExist:
				raise Http404
			membership = CommunityMembership.objects.get(user=request.user.id, community=course.community)
			message = canEditCourse(course.course.state.name, membership.role.name, course.course, request)
			if message != 'True':
				return render(request, 'error.html', {'message':message, 'url':'course_view', 'argument':pk})				
			return render(request, 'edit_course.html', {'course':course, 'topics':topics,'form':form})
	else:
		return redirect('login')

def update_topic_name(request):
	nodeid = request.POST['nodeid']
	name = request.POST['name'+nodeid]
	topic = Topics.objects.get(pk=nodeid)
	topic.name = name
	topic.save()

def move_topic(request):
	parent = request.POST['parent']
	if parent == '':
		parent = None
	else:
		parent = Topics.objects.get(pk=parent)
	topic = request.POST['topic']
	topic = Topics.objects.get(pk=topic)
	if canMove(parent, topic):
		topic.parent = parent
		topic.save()
		return True
	else:
		return False

def canMove(parent, topic):
	cpyParent = parent
	if parent == None: #Root node
		return True
	while cpyParent.parent is not None:
		if cpyParent.parent == topic:
			return False
		cpyParent = cpyParent.parent
	return True

def delete_topic(request):
	deletenodeid = request.POST['deletenodeid']
	topic = Topics.objects.filter(pk=deletenodeid).delete()

def manage_resource(request, pk):
	if request.user.is_authenticated:
		course = Course.objects.get(pk=pk)
		if course.state == States.objects.get(name='draft') and course.created_by != request.user:
			return redirect('home')
		if request.method=='POST':
			topicid =request.POST['topic']
			topic = Topics.objects.get(pk=topicid)
			topic_type = request.POST['topic_type']
			if topic_type=='Youtube' or topic_type=='External':
				topic_link=request.POST['topic_link']
				topic_description=request.POST['topic_description']
				link = Links.objects.create(link = topic_link, desc= topic_description, topics = topic, types=topic_type)
				return redirect('course_view',pk=pk)
			elif topic_type=='PublishedArticle':
				article_id=request.POST['article_id']
				article = Articles.objects.get(pk=article_id)
				topicarticle = TopicArticle.objects.create(topics=topic, article=article)
				return redirect('course_view',pk=pk)
		else:
			try:
				course = CommunityCourses.objects.get(course=pk)
				topics = Topics.objects.filter(course=pk)
				articles = Articles.objects.filter(state__name='publish')
			except CommunityCourses.DoesNotExist:
				raise Http404
			membership = CommunityMembership.objects.get(user=request.user.id, community=course.community)
			message = canEditCourse(course.course.state.name, membership.role.name, course.course, request)
			if message != 'True':
				return render(request, 'error.html', {'message':message, 'url':'course_view', 'argument':pk})
			return render(request, 'manage_resource.html', {'course':course, 'topics':topics, 'articles':articles})
	else:
		return redirect('course_view',pk=pk)


def update_course_info(request,pk):
	if request.user.is_authenticated:
		course = Course.objects.get(pk=pk)
		if course.state == States.objects.get(name='draft') and course.created_by != request.user:
			return redirect('home')
		community = CommunityCourses.objects.get(course=pk)
		uid = request.user.id
		membership = None
		comm = Community.objects.get(pk=community.community.id)
		errormessage = ''
		try:
			membership = CommunityMembership.objects.get(user=uid, community=comm.id)
			if membership:
				if request.method == 'POST':
					title = request.POST['name']
					body = request.POST['desc']
					getstate = request.POST['change_course_state']
					state = States.objects.get(name=getstate)
					course.title = title
					course.body = body
					course.state = state
					try:
						image = request.FILES['course_image']
						course.image = image
					except:
						errormessage = 'image not uploaded'
					course.save()
					return redirect('course_view',pk=pk)
				else:
					message = canEditCourse(course.state.name, membership.role.name, course, request)
					if message != 'True':
						return render(request, 'error.html', {'message':message, 'url':'course_view', 'argument':pk})
					return render(request, 'update_course_info.html', {'course':course, 'membership':membership, 'community':community, 'comm':comm})
			else:
				return redirect('course_view',pk=pk)
		except CommunityMembership.DoesNotExist:
			return redirect('login')
	else:
		return redirect('login')

def canEditCourse(state, role, course, request):
	errormessage = 'True'
	if state=='publishable' and role=='author':
		errormessage = 'Since it is publishable only the publishers can edit this'
	if state=='publishable' and request.user == course.created_by:
		errormessage = 'You cannot edit your own content when it is publishable state'
	if state=='publish':
		errormessage = 'You cannot edit content which is already published'
	return errormessage
