export const registerUser = (req, res) => {
    res.status(200).json({
        success: true,
        message: "Register Controller Working"
    });
};

export const loginUser = (req, res) => {
    res.status(200).json({
        success: true,
        message: "Login Controller Working"
    });
};

export const logoutUser = (req, res) => {
    res.status(200).json({
        success: true,
        message: "Logout Controller Working"
    });
};

export const getCurrentUser = (req, res) => {
    res.status(200).json({
        success: true,
        message: "Current User Controller Working"
    });
};