"""
Views Module
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from nltk.tokenize.treebank import TreebankWordTokenizer
from gnt.adapters import drink_adapter
from gnt.adapters.stt_adapter import IBM
from string import punctuation
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, CreateUserDrinkForm, \
    CreateUserDrinkIngredientForm, CreateUserDrinkInstructionForm
from .models import Profile, Drink, ProfileToLikedDrink, ProfileToDislikedDrink, Friend, FriendRequest, UserDrink, \
    UpvotedUserDrink


def bad_request(request):
    """
    Bad Request View
    """

    return HttpResponseRedirect(reverse('home'))


def home(request):
    """
    Home View
    """

    return render(request, 'gnt/index.html')


def _text_to_dql(text, name_multiplier=1, ingredient_multiplier=1):
    """Converts user input text queries to DQL queries."""
    positive = ''  # DQL for checking drink names/ingredients might include certain words
    negative = ''  # DQL for ensuring drink ingredients exclude certain words
    # stopwords copied from nltk.corpus.stopwords.words('english')
    stopwords = ['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll",
                 "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's",
                 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs',
                 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am',
                 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
                 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while',
                 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during',
                 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over',
                 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
                 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
                 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't",
                 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't",
                 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't",
                 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn',
                 "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won',
                 "won't", 'wouldn', "wouldn't"]
    # additional stopwords that help specific searches
    stopwords += ['drinks', 'recommend']
    # negation stopwords not from any source, we may need to add to this list as we test
    negation_stopwords = ["n't", 'no', 'not', 'nor', 'none', 'never', 'without']
    # split user input into manageable tokens
    tokens = TreebankWordTokenizer().tokenize(
        text)  # NLTKWordTokenizer supposed to be "improved", but destructive module not found
    # track if we're in a negation phrase
    negate = False
    for token in tokens:
        if token in negation_stopwords:
            # start negating every word if we hit a negation stopword
            negate = True
        elif token in punctuation:
            # stop negating every word if we hit a punctuation mark
            negate = False
        elif token in stopwords:
            # ignore any standard stopwords
            continue

        if negate:
            negative += ','  # comma means logical AND
            negative += 'ingredients:!"%s"' % token  # ingredients must not include token
        else:
            positive += '|'  # bar means logical OR
            positive += 'names:"%s"^%d' % (token, name_multiplier)
            positive += '|'
            positive += 'ingredients:"%s"^%d' % (token, ingredient_multiplier)
    # ignore the first character of each sub-query because we started building them with either | or ,
    positive = positive[1:]
    negative = negative[1:]
    # only include parts of the query that actually exist
    if len(positive) > 0:
        if len(negative) > 0:
            query = '(%s),(%s)' % (positive, negative)
        else:
            query = positive
    elif len(negative) > 0:
        query = negative
    else:
        query = ''
    return query


def filter_by_text_presence(drinks, text):
    """Filter drink response list to exclude first drink with name found in the provided text.

    This is useful for 'recommending' drinks to users when they provide the name of a drink."""
    for i, drink in enumerate(drinks):
        if drink['names'][0].lower() in text.lower():
            drinks.pop(i)
            break

    return drinks


def results(request):
    """
    Results View
    """
    if request.method == 'POST':
        if 'audio' in request.FILES:
            audio = request.FILES['audio']
            text = IBM().transcribe(audio)
        else:
            text = request.POST['search_bar']

        # Perform slightly different searches based on what kind of question the user is asking
        if request.POST['question'] == 'what':
            query = _text_to_dql(text, 1, 2) # make drink ingredients more important
        else:
            query = _text_to_dql(text, 2, 1) # make drink names more important

        discovery_adapter = drink_adapter.DiscoveryAdapter()
        response = discovery_adapter.search(query)

        if request.POST['question'] == 'like':
            # if user is looking for similar drinks to a given drink, remove the given drink from the response
            response = filter_by_text_presence(response, text)

        return render(request, 'gnt/results.html', {
            'query': text,
            'drinks': response
        })
    else:
        return HttpResponseRedirect(reverse('home'))


def more_results(request):
    """
    More results with an offset
    """
    text = request.POST['text']
    offset = request.POST['offset']
    discovery_adapter = drink_adapter.DiscoveryAdapter()
    response = discovery_adapter.natural_language_search(text, offset)
    return render(request, 'gnt/drink_results_with_voting.html', {
        'query': text,
        'drinks': response
    })


def register(request):
    """
    Register View
    """

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(
                request, f'Your account has been created! You are now able to log in.')
            return redirect('login')
    else:
        form = UserRegisterForm()

    context = {
        'form': form
    }

    return render(request, 'gnt/register.html', context)


@login_required
def profile_create_drink(request):
    """
    Profile Create Drink View
    """

    IngredientFormset = formset_factory(CreateUserDrinkIngredientForm)
    InstructionFormset = formset_factory(CreateUserDrinkInstructionForm)

    if request.method == 'POST':
        create_user_drink_form = CreateUserDrinkForm(request.POST, request.FILES)

        if create_user_drink_form.is_valid():
            drink = create_user_drink_form.save(commit=False)
            drink.user = request.user
            drink.save()

            ingredient_formset = IngredientFormset(
                request.POST, prefix='ingredient')
            if ingredient_formset.is_valid():
                for ingredient_form in ingredient_formset:
                    ingredient = ingredient_form.save(commit=False)
                    ingredient.drink = drink
                    ingredient.save()

            instruction_formset = InstructionFormset(
                request.POST, prefix='instruction')
            if instruction_formset.is_valid():
                for instruction_form in instruction_formset:
                    instruction = instruction_form.save(commit=False)
                    instruction.drink = drink
                    instruction.save()

                messages.success(
                    request, f'Your drink { drink.name } has been created!')
                return redirect('profile_public', username=request.user.username)
        else:
            name = request.POST['name']
            messages.error(
                request, f'We already have a cocktail named {name}!')
            return redirect('profile_public', username=request.user.username)
    else:
        create_user_drink_form = CreateUserDrinkForm()
        ingredient_formset = IngredientFormset(prefix='ingredient')
        instruction_formset = InstructionFormset(prefix='instruction')

    context = {
        'profile': request.user,
        'create_user_drink_form': create_user_drink_form,
        'ingredient_formset': ingredient_formset,
        'instruction_formset': instruction_formset
    }

    return render(request, 'gnt/profile_create_drink.html', context)


@login_required
def profile_edit(request):
    """
    Profile Edit View
    """

    if request.method == 'POST':
        user_update_form = UserUpdateForm(request.POST, instance=request.user)
        profile_update_form = ProfileUpdateForm(
            request.POST, request.FILES, instance=request.user.profile)

        if user_update_form.is_valid() and profile_update_form.is_valid():
            user_update_form.save()
            profile_update_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('profile_public', username=request.user.username)
    else:
        user_update_form = UserUpdateForm(instance=request.user)
        profile_update_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'profile': request.user,
        'user_update_form': user_update_form,
        'profile_update_form': profile_update_form
    }

    return render(request, 'gnt/profile_edit.html', context)


def profile_public(request, username):
    """
    Profile View
    """
    username = User.objects.get(username=username)
    drinks = UserDrink.objects.filter(user=username).order_by('-timestamp')
    if request.user.is_authenticated:
        requests = (FriendRequest.objects.filter(requestee=request.user.profile) | FriendRequest.objects.filter(requestor=request.user.profile)) & (
            FriendRequest.objects.filter(requestee=username.profile) | FriendRequest.objects.filter(requestor=username.profile))
        friends = (Friend.objects.filter(friend1=username.profile) & Friend.objects.filter(friend2=request.user.profile)) | (
            Friend.objects.filter(friend1=request.user.profile) & Friend.objects.filter(friend2=username.profile))
    else:
        requests = []
        friends = []

    if request.method == 'POST':
        if 'add-friend' in request.POST:
            friend_request = FriendRequest()
            friend_request.requestee = username.profile
            friend_request.requestor = request.user.profile
            friend_request.save()

            messages.success(request, f'Friend request sent to { username }!')
        elif 'remove-friend' in request.POST:
            friend = Friend.objects.filter(friend1=request.user.profile, friend2=username.profile) | Friend.objects.filter(
                friend1=username.profile, friend2=request.user.profile)
            friend.delete()

            messages.info(request, f'Removed friend { username }!')

        elif 'like-drink' in request.POST:
            drink = UserDrink.objects.get(name=request.POST['drink'])
            profile = request.user.profile
            if UpvotedUserDrink.objects.filter(drink=drink, profile=profile).count() == 0:
                drink.likes += 1
                drink.save()
                like = UpvotedUserDrink(drink=drink, profile=profile)
                like.save()

    context = {
        'profile': username,
        'drinks': drinks,
        'requests': requests,
        'friends': friends,
    }

    return render(request, 'gnt/profile_public.html', context)


@login_required
def liked_drinks(request):
    """
    Liked Drinks View
    """

    if request.user.is_authenticated:
        user = request.user
        profile = Profile.objects.get(user=user)
        profile_to_drink = ProfileToLikedDrink.objects.filter(
            profile=profile.id)
        if profile_to_drink:
            response = [0 for i in range(len(profile_to_drink))]
            discovery_adapter = drink_adapter.DiscoveryAdapter()
            for i, ptd in enumerate(profile_to_drink):
                drink = Drink.objects.get(id=ptd.drink.id)
                obj = discovery_adapter.get_drink(drink.drink_hash)
                response[i] = obj[0]

            context = {
                'profile': user,
                'drinks': response
            }
            return render(request, 'gnt/liked_drinks.html', context)
        else:
            context = {
                'profile': user
            }
            return render(request, 'gnt/liked_drinks.html', context)
    else:
        return HttpResponseRedirect('/home/')


def about(request):
    """
    About View
    """

    return render(request, 'gnt/about.html')


def disliked_drinks(request):
    """
    Disliked Drinks View
    """

    if request.user.is_authenticated:
        user = request.user
        profile = Profile.objects.get(user=user)
        profile_to_drink = ProfileToDislikedDrink.objects.filter(
            profile=profile.id)
        if profile_to_drink:
            response = [0 for i in range(len(profile_to_drink))]
            discovery_adapter = drink_adapter.DiscoveryAdapter()
            for i, ptd in enumerate(profile_to_drink):
                drink = Drink.objects.get(id=ptd.drink.id)
                obj = discovery_adapter.get_drink(drink.drink_hash)
                response[i] = obj[0]
            context = {
                'profile': request.user,
                'drinks': response
            }
            return render(request, 'gnt/disliked_drinks.html', context)
        else:
            context = {
                'profile': request.user
            }

            return render(request, 'gnt/disliked_drinks.html', context)
    else:
        return HttpResponseRedirect('/home/')


def timeline_pop(request):
    """
    Timeline View
    """
    offset = 0
    if request.GET.get('offset', 0):
        offset = int(request.GET['offset'])
    drinks = UserDrink.objects.all().order_by('-votes')[offset:offset+50]

    context = {
        'drinks': drinks
    }

    return render(request, 'gnt/timeline.html', context)


def timeline(request):
    """
    Timeline View
    """
    offset = 0
    if request.GET.get('offset', 0) != 0:
        offset = int(request.GET['offset'])
    drinks = UserDrink.objects.all().order_by('-timestamp')[offset:offset+50]

    context = {
        'drinks': drinks
    }

    return render(request, 'gnt/timeline.html', context)


def search(request):
    """
    Search View
    """

    if request.method == 'POST':
        profiles = User.objects.filter(
            username__startswith=request.POST['search_input'])

        context = {
            'profiles': profiles
        }

        return render(request, 'gnt/search.html', context)


def notifications(request, username):
    """
    Notifications View
    """

    requests = FriendRequest.objects.filter(requestee=request.user.profile)

    if request.method == 'POST':
        if 'add-friend' in request.POST:
            requestor = User.objects.get(username=request.POST['requestor'])
            friend_request = FriendRequest.objects.get(
                requestee=request.user.profile, requestor=requestor.profile)
            friend_request.delete()
            friends = Friend(friend1=request.user.profile,
                             friend2=requestor.profile)
            friends.save()

            messages.success(
                request, f'You have added friend { requestor.profile.user }!')

        elif 'deny-friend' in request.POST:
            requestor = User.objects.get(username=request.POST['requestor'])
            friend_request = FriendRequest.objects.get(
                requestee=request.user.profile, requestor=requestor.profile)
            friend_request.delete()

            messages.info(
                request, f'you have denied to add friend { requestor.profile.user }')

    context = {
        'requests': requests
    }

    return render(request, 'gnt/notifications.html', context)


@login_required
def friends(request, username):
    """
    Friends View
    """

    if request.method == 'POST':
        if 'remove-friend' in request.POST:
            requestor = User.objects.get(username=request.POST['requestor'])
            friends = Friend.objects.filter(friend1=requestor.profile, friend2=request.user.profile) | Friend.objects.filter(
                friend1=request.user.profile, friend2=requestor.profile)
            friends.delete()

            messages.success(
                request, f'you have removed friend { requestor.profile.user }')

    friends = Friend.objects.filter(friend1=request.user.profile) | Friend.objects.filter(
        friend2=request.user.profile)

    context = {
        'profile': request.user,
        'friends': friends
    }

    return render(request, 'gnt/friends.html', context)
