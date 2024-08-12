# File Sharing

"File Sharing" (I can't think of an interesting name so it's going to be that for the time being) is a simple and efficient file sharing platform built with Flask. It allows users to upload, share, and manage files with automatic expiration and thumbnail generation for images.

![Showcase image of the web interface](https://github.com/user-attachments/assets/e53993b5-7742-4f4a-bece-8177a0466728)

## Features

- File upload with automatic expiration
- File listing and sharing
- File preview
- Storage usage information
- Responsive web interface
- Mobile friendly

## File Structure

```
file-sharing-web/
├── app.py
├── requirements.txt
├── README.md
├── uploads/
├── thumbnails/
└── templates/
    ├── index.html
    └── share.html
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/airi103/file-sharing-web.git
cd file-sharing-web
```

2. Install the required Python packages:
```py
pip install -r requirements.txt
```

## Running the Application
To start the server, run the following command:

```py
python app.py --host 0.0.0.0 --port 5000
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
