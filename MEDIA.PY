from django.shortcuts import render

from users.forms import UserRegistrationForm

def base(request):
    return render(request,'base.html')



def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'You have been successfully registered') 
            return render(request,'UserRegistration.html')
        else:
            messages.error(request, 'Email or Mobile Already Exists')
    else:
        form = UserRegistrationForm()
    return render(request, 'UserRegistration.html', {'form': form})


from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UserRegistrationModel

# In views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UserRegistrationModel

def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('password')  # Corrected key to match the form input name
        try:
            user = UserRegistrationModel.objects.get(loginid=loginid, password=pswd)
            if user.status == "activated":
                request.session['id'] = user.id
                request.session['loggeduser'] = user.name
                return redirect('UserHome')  # Redirect to User Home after successful login
            else:
                messages.error(request, 'Your account is not activated.')
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, 'Invalid Login ID or Password')
    return render(request, 'UserLogin.html')  # Ensure this is the correct template name


def UserHome(request):
    return render(request, 'users/UserHome.html')



    ######################## dl code #################################

import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import tensorflow as tf
from tensorflow.keras import layers, models
from django.shortcuts import render
from django.conf import settings

def training(request):
    # Set the already extracted dataset path (no ZIP handling needed)
    base_dir = os.path.join(settings.MEDIA_ROOT, 'archive')
    image_dir = os.path.join(base_dir, 'all_images', 'images')
    mask_dir = os.path.join(base_dir, 'all_masks', 'masks')
    IMG_SIZE = (128, 128)

    # Check if dataset folders exist
    if not os.path.exists(image_dir) or not os.path.exists(mask_dir):
        return render(request, 'users/training.html', {
            'error': f"❌ Dataset folder not found. Please ensure the following paths exist:<br>"
                     f"<code>{image_dir}</code><br><code>{mask_dir}</code>"
        })

    # Function to load and resize images from a folder
    def load_images(folder, size=IMG_SIZE, color=cv2.IMREAD_COLOR):
        images = []
        for file in sorted(os.listdir(folder)):
            path = os.path.join(folder, file)
            img = cv2.imread(path, color)
            if img is not None:
                img = cv2.resize(img, size)
                images.append(img)
        return np.array(images)

    # Load images and masks
    X = load_images(image_dir) / 255.0
    Y = load_images(mask_dir, color=cv2.IMREAD_GRAYSCALE)
    Y = np.expand_dims(Y, axis=-1)  # Add channel dimension
    Y = (Y > 127).astype(np.uint8)  # Binarize masks

    # Train/test split
    X_train, X_val, Y_train, Y_val = train_test_split(X, Y, test_size=0.2, random_state=42)

    # Define U-Net model
    def build_unet(input_size=(128, 128, 3)):
        inputs = layers.Input(input_size)
        c1 = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(inputs)
        c1 = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(c1)
        p1 = layers.MaxPooling2D((2, 2))(c1)

        c2 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(p1)
        c2 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(c2)
        p2 = layers.MaxPooling2D((2, 2))(c2)

        c3 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(p2)
        c3 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(c3)

        u1 = layers.UpSampling2D((2, 2))(c3)
        u1 = layers.Concatenate()([u1, c2])
        c4 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(u1)
        c4 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(c4)

        u2 = layers.UpSampling2D((2, 2))(c4)
        u2 = layers.Concatenate()([u2, c1])
        c5 = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(u2)
        c5 = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(c5)

        outputs = layers.Conv2D(1, (1, 1), activation='sigmoid')(c5)
        model = models.Model(inputs, outputs)
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model

    # Train model
    model = build_unet()
    history = model.fit(
        X_train, Y_train,
        validation_data=(X_val, Y_val),
        batch_size=8,
        epochs=15,
        verbose=1
    )

    # Save model
    model_path = os.path.join(settings.MEDIA_ROOT, 'unet_cell_counting_model.h5')
    model.save(model_path)

    # Predict and flatten
    Y_pred = (model.predict(X_val) > 0.5).astype(np.uint8)
    y_true = Y_val.flatten()
    y_pred = Y_pred.flatten()

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    cm_plot_path = os.path.join(settings.MEDIA_ROOT, 'confusion_matrix.png')
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot(cmap='Blues')
    plt.title("Confusion Matrix")
    plt.savefig(cm_plot_path)
    plt.close()

    # Render to template
    return render(request, 'users/training.html', {
        'accuracy': round(history.history['val_accuracy'][-1] * 100, 2),
        'loss': round(history.history['val_loss'][-1], 4),
        'confusion_matrix': cm.tolist(),
        'confusion_matrix_plot': 'media/confusion_matrix.png',
        'model_path': 'media/unet_cell_counting_model.h5',
    })


import os
import numpy as np
import cv2
import tensorflow as tf
from django.shortcuts import render
from django.contrib import messages
from django.conf import settings

# Load model only once
MODEL_PATH = os.path.join(settings.BASE_DIR, 'media', 'star_galaxy_classifier.h5')
model = tf.keras.models.load_model(MODEL_PATH)
label_map = {0: "Star", 1: "Galaxy"}

def preprocess_image(img):
    img = cv2.resize(img, (64, 64))
    img = img / 255.0  # Normalize
    return np.expand_dims(img, axis=0)  # Add batch dim

def predict_image(img_array):
    prob = model.predict(img_array)[0][0]
    label = 1 if prob > 0.5 else 0
    return label_map[label], prob

def prediction(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            img_file = request.FILES['image']
            img_array = np.frombuffer(img_file.read(), np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if img is None:
                messages.error(request, 'Invalid image format.')
                return render(request, 'users/prediction.html')

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            input_array = preprocess_image(img_rgb)
            pred_label, prob = predict_image(input_array)

            # Save image to media/uploads/
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            img_path = os.path.join(upload_dir, img_file.name)
            cv2.imwrite(img_path, img)
            img_url = os.path.join(settings.MEDIA_URL, 'uploads', img_file.name)

            return render(request, 'users/prediction.html', {
                'pred_label': pred_label,
                'prob': f"{prob:.2f}",
                'img_url': img_url
            })

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    return render(request, 'users/prediction.html')
