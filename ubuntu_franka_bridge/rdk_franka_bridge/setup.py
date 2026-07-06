from setuptools import setup

package_name = "rdk_franka_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="RDK Team",
    maintainer_email="student@example.com",
    description="RDK to Franka ROS 2 command bridge",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "command_server = rdk_franka_bridge.command_server:main",
            "command_executor = rdk_franka_bridge.command_executor:main",
        ],
    },
)
