#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD ICP 定位节点
================
将 D435 实时深度点云用 GICP 对齐到 CAD 导出的 .ply 模型，
输出 base_link 在 map 帧中的位姿（PoseWithCovarianceStamped + 可选 TF）。

工作原理：
  1. 启动时一次性加载 CAD .ply，体素降采样 + 估计法线
  2. 实时点云每 1/icp_rate 秒做一次 GICP，初值用上次输出
  3. 监听 /initialpose（如 RViz 的 2D Pose Estimate）随时重置
  4. ICP fitness 低时保持上次位姿，仅打 warning（不发布坏数据）
  5. 输出话题 /cad_pose，可选发布 map->base_link TF

参数（私有命名空间）：
  ~cad_path                       CAD .ply 路径（必填）
  ~cad_scale                      CAD 单位缩放（默认 1.0；CAD 是 mm 时填 0.001）
  ~cad_axis_remap                 CAD 轴重排, 3 字符 xyz 排列（默认 'xyz' 不变）
                                  'xzy' = Y-up CAD → Z-up map（Y/Z 互换）
                                  含义: 新坐标 = 旧坐标的指定列
  ~point_cloud_topic              D435 点云话题（默认 /camera/depth/color/points）
  ~camera_frame                   D435 点云的 frame_id（默认 camera_color_optical_frame）
  ~map_frame                      地图坐标系（默认 map）
  ~base_frame                     机器人基座（默认 base_link）
  ~icp_rate                       ICP 频率 Hz（默认 5）
  ~voxel_size                     体素降采样大小 m（默认 0.05）
  ~max_correspondence_distance    ICP 最大对应距离 m（默认 0.2）
  ~publish_tf                     是否发布 map->base_link TF（默认 true）
  ~min_fitness                    ICP 失败判定阈值（默认 0.3）
  ~initial_x / _y / _z / _yaw     初始位姿（默认 0,0,0,0）
"""

import os
import sys
import threading

import numpy as np
import rospy
import tf2_ros
from geometry_msgs.msg import PoseWithCovarianceStamped, TransformStamped
from sensor_msgs.msg import PointCloud2
import sensor_msgs.point_cloud2 as pc2
from tf.transformations import (
    euler_from_quaternion,
    quaternion_from_euler,
    quaternion_from_matrix,
    quaternion_matrix,
)

try:
    import open3d as o3d
except ImportError:
    sys.stderr.write(
        "[cad_icp_localizer] 未找到 open3d，请先安装：pip install open3d\n")
    sys.exit(1)


def pose_to_matrix(x, y, z, roll, pitch, yaw):
    T = quaternion_matrix(quaternion_from_euler(roll, pitch, yaw))
    T[0, 3] = x
    T[1, 3] = y
    T[2, 3] = z
    return T


def matrix_to_xyz_quat(T):
    q = quaternion_from_matrix(T)
    return T[0, 3], T[1, 3], T[2, 3], q[0], q[1], q[2], q[3]


class CADIcpLocalizer:
    def __init__(self):
        rospy.init_node('cad_icp_localizer')

        self.cad_path = rospy.get_param('~cad_path')
        self.cad_scale = float(rospy.get_param('~cad_scale', 1.0))
        self.cad_axis_remap = str(
            rospy.get_param('~cad_axis_remap', 'xyz')).lower()
        self.cloud_topic = rospy.get_param(
            '~point_cloud_topic', '/camera/depth/color/points')
        self.camera_frame = rospy.get_param(
            '~camera_frame', 'camera_color_optical_frame')
        self.map_frame = rospy.get_param('~map_frame', 'map')
        self.base_frame = rospy.get_param('~base_frame', 'base_link')
        self.icp_rate = float(rospy.get_param('~icp_rate', 5.0))
        self.voxel_size = float(rospy.get_param('~voxel_size', 0.05))
        self.max_corresp_dist = float(
            rospy.get_param('~max_correspondence_distance', 0.2))
        self.publish_tf = bool(rospy.get_param('~publish_tf', True))
        self.min_fitness = float(rospy.get_param('~min_fitness', 0.3))

        x = float(rospy.get_param('~initial_x', 0.0))
        y = float(rospy.get_param('~initial_y', 0.0))
        z = float(rospy.get_param('~initial_z', 0.0))
        yaw = float(rospy.get_param('~initial_yaw', 0.0))

        self.pose = pose_to_matrix(x, y, z, 0.0, 0.0, yaw)
        self.pose_lock = threading.Lock()

        self._load_cad()

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()

        self.latest_cloud_msg = None
        self.cloud_lock = threading.Lock()

        self.cloud_sub = rospy.Subscriber(
            self.cloud_topic, PointCloud2, self._cloud_cb,
            queue_size=1, buff_size=2 ** 24)
        self.init_sub = rospy.Subscriber(
            '/initialpose', PoseWithCovarianceStamped, self._initpose_cb,
            queue_size=1)

        self.pose_pub = rospy.Publisher(
            '/cad_pose', PoseWithCovarianceStamped, queue_size=10)

        self.icp_timer = rospy.Timer(
            rospy.Duration(1.0 / self.icp_rate), self._icp_cb)

        rospy.loginfo("CAD ICP localizer 启动 (rate=%.1fHz, voxel=%.3fm, "
                      "max_corr=%.2fm, init=(%.2f, %.2f, %.1f deg))",
                      self.icp_rate, self.voxel_size, self.max_corresp_dist,
                      x, y, np.degrees(yaw))

    def _resolve_cad_path(self, path):
        if os.path.isfile(path):
            return path
        d = os.path.dirname(path) or '.'
        target = os.path.basename(path).lower()
        if not os.path.isdir(d):
            return None
        for f in os.listdir(d):
            if f.lower() == target:
                hit = os.path.join(d, f)
                rospy.logwarn("CAD 路径大小写不匹配, 实际找到: %s", hit)
                return hit
        return None

    def _load_cad(self):
        self.cad = None
        resolved = self._resolve_cad_path(self.cad_path)
        if resolved is None:
            rospy.logerr("CAD 文件不存在: %s — 节点保持运行但不发布 /cad_pose",
                         self.cad_path)
            return
        self.cad_path = resolved

        rospy.loginfo("加载 CAD: %s", self.cad_path)

        cad_raw = o3d.io.read_point_cloud(self.cad_path)
        if len(cad_raw.points) == 0:
            mesh = o3d.io.read_triangle_mesh(self.cad_path)
            if len(mesh.vertices) == 0:
                rospy.logerr("CAD 既不是有效点云也不是 mesh: %s — 节点保持运行但不发布 /cad_pose",
                             self.cad_path)
                return
            rospy.loginfo("CAD 是 mesh，从表面采样 200000 点")
            cad_raw = mesh.sample_points_uniformly(number_of_points=200000)

        if self.cad_scale != 1.0:
            pts = np.asarray(cad_raw.points) * self.cad_scale
            cad_raw.points = o3d.utility.Vector3dVector(pts)
            rospy.loginfo("CAD 应用缩放: x %.6f", self.cad_scale)

        if self.cad_axis_remap != 'xyz':
            idx = {'x': 0, 'y': 1, 'z': 2}
            try:
                cols = [idx[c] for c in self.cad_axis_remap]
                if len(cols) != 3 or sorted(cols) != [0, 1, 2]:
                    raise ValueError("axis_remap 必须是 xyz 的排列")
                pts = np.asarray(cad_raw.points)[:, cols]
                cad_raw.points = o3d.utility.Vector3dVector(pts)
                rospy.loginfo("CAD 轴重排: xyz → %s", self.cad_axis_remap)
            except Exception as e:
                rospy.logwarn("CAD 轴重排失败 (%s): %s — 跳过",
                              self.cad_axis_remap, e)

        pts = np.asarray(cad_raw.points)
        rng = pts.max(axis=0) - pts.min(axis=0)
        rospy.loginfo("CAD 边界: min=[%.2f,%.2f,%.2f] max=[%.2f,%.2f,%.2f] "
                      "size=%.2fx%.2fx%.2fm",
                      *pts.min(axis=0), *pts.max(axis=0), *rng)
        if (rng > 100).any():
            rospy.logwarn(
                "!! CAD 任一维 > 100m, 单位很可能是 mm. 设 cad_scale=0.001")

        rospy.loginfo("CAD 原始点数: %d", len(cad_raw.points))
        self.cad = cad_raw.voxel_down_sample(voxel_size=self.voxel_size)
        self.cad.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=self.voxel_size * 2.0, max_nn=30))
        rospy.loginfo("CAD 降采样后点数: %d (voxel=%.3fm)",
                      len(self.cad.points), self.voxel_size)

    def _cloud_cb(self, msg):
        with self.cloud_lock:
            self.latest_cloud_msg = msg

    def _initpose_cb(self, msg):
        p = msg.pose.pose
        q = [p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w]
        T = quaternion_matrix(q)
        T[0, 3] = p.position.x
        T[1, 3] = p.position.y
        T[2, 3] = p.position.z
        with self.pose_lock:
            self.pose = T
        rospy.loginfo("收到 /initialpose: (%.2f, %.2f, yaw=%.1f deg)",
                      T[0, 3], T[1, 3],
                      np.degrees(euler_from_quaternion(q)[2]))

    def _cloud_msg_to_o3d(self, msg):
        pts = np.array(
            list(pc2.read_points(msg, field_names=('x', 'y', 'z'),
                                 skip_nans=True)),
            dtype=np.float32)
        if len(pts) == 0:
            return None
        cloud = o3d.geometry.PointCloud()
        cloud.points = o3d.utility.Vector3dVector(pts.astype(np.float64))
        return cloud

    def _get_base_to_camera(self):
        try:
            t = self.tf_buffer.lookup_transform(
                self.base_frame, self.camera_frame,
                rospy.Time(0), rospy.Duration(1.0))
            tr = t.transform.translation
            r = t.transform.rotation
            T = quaternion_matrix([r.x, r.y, r.z, r.w])
            T[0, 3] = tr.x
            T[1, 3] = tr.y
            T[2, 3] = tr.z
            return T
        except Exception as e:
            rospy.logwarn_throttle(5.0, "查 TF 失败 (%s -> %s): %s",
                                   self.base_frame, self.camera_frame, str(e))
            return None

    def _icp_cb(self, _event):
        if self.cad is None:
            return
        with self.cloud_lock:
            msg = self.latest_cloud_msg
        if msg is None:
            return

        cloud = self._cloud_msg_to_o3d(msg)
        if cloud is None or len(cloud.points) < 100:
            rospy.logwarn_throttle(
                2.0, "实时点云空或太稀疏 (%d pts)",
                0 if cloud is None else len(cloud.points))
            return

        cloud_ds = cloud.voxel_down_sample(voxel_size=self.voxel_size)
        cloud_ds.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=self.voxel_size * 2.0, max_nn=30))

        with self.pose_lock:
            T_map_base = self.pose.copy()

        T_base_cam = self._get_base_to_camera()
        if T_base_cam is None:
            return

        T_init_map_cam = T_map_base @ T_base_cam

        # open3d 0.13 没有 GeneralizedICP, 退化到 PointToPlane (target 已有 normals)
        # 0.16+ 优先用 GICP
        reg = o3d.pipelines.registration
        if hasattr(reg, 'TransformationEstimationForGeneralizedICP'):
            estimator = reg.TransformationEstimationForGeneralizedICP()
            icp_fn = getattr(reg, 'registration_generalized_icp',
                             reg.registration_icp)
        else:
            estimator = reg.TransformationEstimationPointToPlane()
            icp_fn = reg.registration_icp

        result = icp_fn(
            cloud_ds, self.cad,
            self.max_corresp_dist,
            T_init_map_cam,
            estimator,
            reg.ICPConvergenceCriteria(max_iteration=30))

        if result.fitness < self.min_fitness:
            rospy.logwarn_throttle(
                2.0, "ICP fitness 低: %.3f rmse=%.3f 内点=%d",
                result.fitness, result.inlier_rmse,
                len(result.correspondence_set))
            return

        T_map_cam = np.asarray(result.transformation)
        T_map_base_new = T_map_cam @ np.linalg.inv(T_base_cam)

        with self.pose_lock:
            self.pose = T_map_base_new

        self._publish_pose(T_map_base_new, msg.header.stamp)
        if self.publish_tf:
            self._publish_tf(T_map_base_new, msg.header.stamp)

        yaw = euler_from_quaternion(
            quaternion_from_matrix(T_map_base_new))[2]
        rospy.loginfo_throttle(
            2.0, "ICP OK fitness=%.3f rmse=%.4f pts=%d pose=(%.2f, %.2f, "
                 "yaw=%.1f deg)",
            result.fitness, result.inlier_rmse, len(cloud_ds.points),
            T_map_base_new[0, 3], T_map_base_new[1, 3], np.degrees(yaw))

    def _publish_pose(self, T, stamp):
        x, y, z, qx, qy, qz, qw = matrix_to_xyz_quat(T)
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = self.map_frame
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.position.z = z
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        cov = [0.0] * 36
        cov[0] = cov[7] = cov[14] = 0.05 ** 2
        cov[21] = cov[28] = cov[35] = (np.radians(2.0)) ** 2
        msg.pose.covariance = cov
        self.pose_pub.publish(msg)

    def _publish_tf(self, T, stamp):
        x, y, z, qx, qy, qz, qw = matrix_to_xyz_quat(T)
        msg = TransformStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = self.map_frame
        msg.child_frame_id = self.base_frame
        msg.transform.translation.x = x
        msg.transform.translation.y = y
        msg.transform.translation.z = z
        msg.transform.rotation.x = qx
        msg.transform.rotation.y = qy
        msg.transform.rotation.z = qz
        msg.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(msg)

    def run(self):
        rospy.spin()


if __name__ == '__main__':
    try:
        CADIcpLocalizer().run()
    except rospy.ROSInterruptException:
        pass
